#include "../include/wol.h"
#include "../include/socket_utils.h"
#include <cstring>
#include <vector>
#include <sstream>
#include <iostream>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#endif

namespace nexus::wol {

static std::vector<uint8_t> parse_mac(const std::string& mac) {
    std::vector<uint8_t> result(6);
    std::string clean;
    
    // Убираем двоеточия и дефисы
    for (char c : mac) {
        if (c != ':' && c != '-' && c != ' ') clean += c;
    }
    
    if (clean.size() != 12) {
        std::cerr << "[WOL] Invalid MAC: " << mac << std::endl;
        return {};
    }
    
    for (int i = 0; i < 6; i++) {
        std::string byteStr = clean.substr(i * 2, 2);
        result[i] = (uint8_t)std::stoi(byteStr, nullptr, 16);
    }
    
    return result;
}

bool send_magic_packet(const std::string& mac_address) {
    auto mac = parse_mac(mac_address);
    if (mac.empty()) return false;
    
    // Magic Packet: 6 байт 0xFF + 16 раз MAC
    std::vector<uint8_t> packet(102);
    memset(packet.data(), 0xFF, 6);
    for (int i = 0; i < 16; i++) {
        memcpy(packet.data() + 6 + i * 6, mac.data(), 6);
    }
    
    // Отправляем broadcast на порт 7 или 9
    sockets_init();
    
    socket_t s = ::socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (s < 0) {
        std::cerr << "[WOL] Socket failed\n";
        return false;
    }
    
    // Разрешаем broadcast
    int broadcast = 1;
    setsockopt(s, SOL_SOCKET, SO_BROADCAST,
#ifdef _WIN32
        (const char*)&broadcast,
#else
        &broadcast,
#endif
        sizeof(broadcast));
    
    struct sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(9);
    addr.sin_addr.s_addr = inet_addr("255.255.255.255");
    
    int sent = sendto(s, (const char*)packet.data(), (int)packet.size(), 0,
                     (struct sockaddr*)&addr, sizeof(addr));
    
    close_socket(s);
    
    if (sent == (int)packet.size()) {
        std::cout << "[WOL] Magic packet sent to " << mac_address << std::endl;
        return true;
    }
    
    std::cerr << "[WOL] Failed to send: " << sent << std::endl;
    return false;
}

} // namespace nexus::wol
