#include <cstring>
#include "../include/socket_utils.h"
#include "../include/websocket_utils.h"
#include "../include/wol.h"

#include <csignal>
#include <iostream>
#include <thread>
#include <string>
#include <mutex>
#include <sstream>
#include <unordered_map>
#include <vector>

static std::unordered_map<std::string, socket_t> peers;
static std::mutex peers_mutex;

static std::string read_http_request(socket_t s) {
    std::string request;
    char buf[512];
    while (request.find("\r\n\r\n") == std::string::npos) {
        int n = recv(s, buf, sizeof(buf), 0);
        if (n <= 0) return {};
        request.append(buf, n);
    }
    return request;
}

static bool parse_websocket_key(const std::string &request, std::string &key) {
    std::istringstream stream(request);
    std::string line;
    while (std::getline(stream, line) && line != "\r") {
        if (line.rfind("Sec-WebSocket-Key:", 0) == 0) {
            key = line.substr(strlen("Sec-WebSocket-Key:"));
            while (!key.empty() && (key.front() == ' ' || key.front() == '\t')) key.erase(0, 1);
            if (!key.empty() && key.back() == '\r') key.pop_back();
            return true;
        }
    }
    return false;
}

static bool send_websocket_handshake(socket_t s, const std::string &accept_key) {
    std::string response =
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Accept: " + accept_key + "\r\n\r\n";
    return send(s, response.data(), (int)response.size(), 0) == (int)response.size();
}

static bool send_frame(socket_t s, const std::string &message) {
    std::string frame = build_websocket_frame(message);
    return send(s, frame.data(), (int)frame.size(), 0) == (int)frame.size();
}

static bool register_peer(const std::string &peer_id, socket_t s) {
    std::lock_guard<std::mutex> lock(peers_mutex);
    if (peers.find(peer_id) != peers.end()) return false;
    peers[peer_id] = s;
    return true;
}

static void unregister_peer(socket_t s) {
    std::lock_guard<std::mutex> lock(peers_mutex);
    for (auto it = peers.begin(); it != peers.end();) {
        if (it->second == s) it = peers.erase(it);
        else ++it;
    }
}

static bool route_message(const std::string &from_id, const std::string &to_id, const std::string &cmd, const std::string &payload) {
    std::lock_guard<std::mutex> lock(peers_mutex);
    auto it = peers.find(to_id);
    if (it == peers.end()) return false;
    std::string message = "FROM " + from_id + " " + cmd + " " + std::to_string(payload.size()) + "\n" + payload;
    return send_frame(it->second, message);
}

static bool parse_register_message(const std::string &message, std::string &peer_id) {
    std::istringstream iss(message);
    std::string command;
    iss >> command;
    if (command != "REGISTER") return false;
    iss >> peer_id;
    return !peer_id.empty();
}

static bool has_flag(int argc, char** argv, const std::string &name) {
    for (int i = 1; i < argc; ++i) {
        if (name == argv[i]) return true;
    }
    return false;
}

static uint16_t parse_port_arg(int argc, char** argv, uint16_t default_port) {
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--port" && i + 1 < argc) {
            return static_cast<uint16_t>(std::stoi(argv[i + 1]));
        }
        const std::string prefix = "--port=";
        if (arg.rfind(prefix, 0) == 0) {
            return static_cast<uint16_t>(std::stoi(arg.substr(prefix.size())));
        }
        if (arg[0] != '-') {
            return static_cast<uint16_t>(std::stoi(arg));
        }
    }
    return default_port;
}

static void log_peers() {
    std::lock_guard<std::mutex> lock(peers_mutex);
    std::cout << "Active peers [" << peers.size() << "]: ";
    bool first = true;
    for (const auto &entry : peers) {
        if (!first) std::cout << ", ";
        std::cout << entry.first;
        first = false;
    }
    std::cout << "\n";
}

static bool parse_command_payload(const std::string &message,
                                  std::string &command,
                                  std::string &target,
                                  std::string &payload) {
    std::istringstream iss(message);
    iss >> command;
    if (command == "OFFER" || command == "ANSWER") {
        size_t length = 0;
        iss >> target >> length;
        if (target.empty() || !iss) return false;
        size_t split = message.find('\n');
        if (split == std::string::npos) return false;
        payload = message.substr(split + 1);
        if (payload.size() != length) return false;
        return true;
    }
    if (command == "LIST" || command == "UNREGISTER") {
        return true;
    }
    return false;
}


// HTTP health check for Render
static bool handle_http_health(socket_t s, const char* data, int len) {
    if (len >= 4 && strncmp(data, "GET ", 4) == 0) {
        const char* response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nNexus Server OK";
        send(s, response, (int)strlen(response), 0);
        close_socket(s);
        return true;
    }
    return false;
}

static bool handshake_and_join(socket_t s, std::string &peer_id) {
std::string request = read_http_request(s);
    if (request.empty()) return false;
    std::string key;
    if (!parse_websocket_key(request, key)) return false;
    std::string accept_key = make_websocket_accept(key);
    if (!send_websocket_handshake(s, accept_key)) return false;

    std::string buffer;
    char recvbuf[2048];
    while (true) {
        int n = recv(s, recvbuf, sizeof(recvbuf), 0);
        if (n <= 0) return false;
        buffer.append(recvbuf, n);
        std::string message = read_websocket_payload(buffer);
        if (!message.empty()) {
            if (!parse_register_message(message, peer_id)) return false;
            if (!register_peer(peer_id, s)) return false;
            std::cout << "Peer registered: " << peer_id << "\n";
            log_peers();
            send_frame(s, "REGISTERED " + peer_id);
            return true;
        }
    }
}

static void client_thread(socket_t s) {
    // HTTP health check for Render
    char peek[4] = {};
    if (recv(s, peek, 4, MSG_PEEK) >= 4 && peek[0] == char(71) && peek[1] == char(69) && peek[2] == char(84)) {
        const char* ok = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nOK";
        send(s, ok, (int)strlen(ok), 0);
        close_socket(s);
        return;
    }
    std::string peer_id;
    if (!handshake_and_join(s, peer_id)) {
        close_socket(s);
        return;
    }

    std::string buffer;
    char recvbuf[2048];
    while (true) {
        int n = recv(s, recvbuf, sizeof(recvbuf), 0);
        if (n <= 0) break;
        buffer.append(recvbuf, n);
        std::string message = read_websocket_payload(buffer);
        if (!message.empty()) {
            std::string command;
            std::string target;
            std::string payload;
            if (!parse_command_payload(message, command, target, payload)) {
                send_frame(s, "ERROR invalid_message_format");
                buffer.clear();
                continue;
            }

            if (command == "LIST") {
                std::lock_guard<std::mutex> lock(peers_mutex);
                std::string response = "PEERS";
                for (auto &entry : peers) {
                    if (entry.first == peer_id) continue;
                    response += " ";
                    response += entry.first;
                }
                send_frame(s, response);
                std::cout << "Peer " << peer_id << " requested peer list\n";
                log_peers();
            } else if (command == "WOL") {
                std::string mac = payload;
                if (nexus::wol::send_magic_packet(mac)) {
                    send_frame(s, "WOL_OK");
                } else {
                    send_frame(s, "WOL_FAIL");
                }`n            } else if (command == "UNREGISTER") {
                send_frame(s, "UNREGISTERED");
                std::cout << "Peer unregistered: " << peer_id << "\n";
                log_peers();
                break;
            } else if (command == "OFFER" || command == "ANSWER") {
                if (!route_message(peer_id, target, command, payload)) {
                    send_frame(s, "ERROR target_not_found");
                }
            } else {
                send_frame(s, "ERROR unknown_command");
            }
            buffer.clear();
        }
    }

    unregister_peer(s);
    close_socket(s);
}

int main(int argc, char** argv) {
    uint16_t port = parse_port_arg(argc, argv, 10000);
    bool deploy_mode = has_flag(argc, argv, "--deploy");

    sockets_init();
    socket_t listen_sock = create_listen_socket(port);
    if (listen_sock < 0) return 1;
    std::cout << "WebSocket signaling server listening on " << port;
    if (deploy_mode) std::cout << " (deploy mode)";
    std::cout << "\n";
    if (deploy_mode) {
        std::cout << "Deploy mode: enabling production signaling server settings\n";
    }

    while (true) {
        socket_t s = accept_client(listen_sock);
        if (s < 0) continue;
        std::thread(client_thread, s).detach();
    }

    close_socket(listen_sock);
    sockets_cleanup();
    return 0;
}



