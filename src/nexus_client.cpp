#include "../include/nexus_client.h"
#include <iostream>
#include <sstream>

namespace nexus::client {

NexusClient::NexusClient(const std::string& host, uint16_t port)
    : serverHost(host), serverPort(port) {}

NexusClient::~NexusClient() { disconnect(); }

bool NexusClient::connect(const std::string& deviceId, const std::string& password) {
    sockets_init();
    sock = connect_to_host(serverHost, serverPort);
    if (sock < 0) { std::cerr << "[Client] Failed to connect to server\n"; return false; }
    
    // WebSocket upgrade
    std::string request = "GET /ws HTTP/1.1\r\nHost: " + serverHost + "\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==\r\nSec-WebSocket-Version: 13\r\n\r\n";
    send(sock, request.c_str(), (int)request.size(), 0);
    
    char buf[1024];
    int n = recv(sock, buf, sizeof(buf)-1, 0);
    if (n <= 0) { close_socket(sock); return false; }
    
    // Register with device ID and password
    std::string regMsg = "CONNECT " + deviceId + " " + password;
    std::string frame = build_websocket_frame(regMsg, true);
    send(sock, frame.c_str(), (int)frame.size(), 0);
    
    // Wait for response
    n = recv(sock, buf, sizeof(buf)-1, 0);
    if (n <= 0) { close_socket(sock); return false; }
    
    std::string response = read_websocket_payload(std::string(buf, n));
    if (response.find("CONNECTED") == 0) {
        connected = true;
        running = true;
        recvThread = std::make_unique<std::thread>(&NexusClient::readLoop, this);
        std::cout << "[Client] Connected to device: " << deviceId << "\n";
        return true;
    }
    
    std::cerr << "[Client] Connection rejected: " << response << "\n";
    close_socket(sock);
    return false;
}

void NexusClient::disconnect() {
    running = false;
    if (recvThread && recvThread->joinable()) recvThread->join();
    if (sock >= 0) close_socket(sock);
    connected = false;
}

void NexusClient::readLoop() {
    char buf[65536];
    while (running) {
        int n = recv(sock, buf, sizeof(buf)-1, 0);
        if (n <= 0) { running = false; break; }
        
        std::string payload = read_websocket_payload(std::string(buf, n));
        if (payload.empty()) continue;
        
        // Parse frame: "FRAME <w> <h> <size>\n<data>"
        if (payload.find("FRAME ") == 0) {
            std::istringstream iss(payload.substr(6));
            uint32_t w, h; size_t size;
            iss >> w >> h >> size;
            size_t headerEnd = payload.find('\n') + 1;
            if (onFrame && payload.size() >= headerEnd + size) {
                onFrame((const uint8_t*)payload.data() + headerEnd, size, w, h);
            }
        }
    }
    connected = false;
}

void NexusClient::sendFrame(const std::string& msg) {
    if (connected) {
        std::string frame = build_websocket_frame(msg, true);
        send(sock, frame.c_str(), (int)frame.size(), 0);
    }
}

} // namespace nexus::client
