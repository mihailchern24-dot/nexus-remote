#include "../include/stun.h"
#include "../include/socket_utils.h"
// arpa/inet.h - not needed on Windows
// unistd.h - not needed on Windows
#include <cstring>
#include <random>
#include <vector>
#include <iostream>
#ifdef _WIN32
#include <ws2tcpip.h>
#endif
#include <iostream>
#ifdef _WIN32
#include <ws2tcpip.h>
#endif

static uint16_t get_transaction_id(uint8_t id[12]) {
    static std::mt19937 rng((uint32_t)std::random_device{}());
    for (int i = 0; i < 12; ++i) id[i] = (uint8_t)(rng() & 0xFF);
    return 0;
}

std::pair<std::string, uint16_t> stun_get_public_endpoint(const std::string &server_host, uint16_t server_port) {
    socket_t s = ::socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (s < 0) return {"", 0};

    struct sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(server_port);
    server_addr.sin_addr.s_addr = inet_addr(server_host.c_str());
    if (server_addr.sin_addr.s_addr == INADDR_NONE) {
        struct addrinfo hints{};
        hints.ai_family = AF_INET;
        hints.ai_socktype = SOCK_DGRAM;
        struct addrinfo *res = nullptr;
        if (getaddrinfo(server_host.c_str(), nullptr, &hints, &res) != 0 || !res) {
            close_socket(s);
            return {"", 0};
        }
        server_addr = *(struct sockaddr_in*)res->ai_addr;
        server_addr.sin_port = htons(server_port);
        freeaddrinfo(res);
    }

    uint8_t request[20] = {0};
    request[0] = 0x00;
    request[1] = 0x01;
    uint16_t msg_len = 0;
    request[2] = (msg_len >> 8) & 0xFF;
    request[3] = msg_len & 0xFF;
    request[4] = 0x21;
    request[5] = 0x12;
    request[6] = 0xA4;
    request[7] = 0x42;
    get_transaction_id(request + 8);

    if (sendto(s, (const char*)request, sizeof(request), 0, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        close_socket(s);
        return {"", 0};
    }

    uint8_t response[576];
    struct sockaddr_in from{};
    socklen_t fromlen = sizeof(from);
    int n = recvfrom(s, (char*)response, sizeof(response), 0, (struct sockaddr*)&from, &fromlen);
    if (n <= 0) {
        close_socket(s);
        return {"", 0};
    }

    close_socket(s);

    if (n < 20 || response[0] != 0x01 || response[1] != 0x01) return {"", 0};
    uint16_t length = (response[2] << 8) | response[3];
    size_t pos = 20;
    while (pos + 4 <= (size_t)n) {
        uint16_t type = (response[pos] << 8) | response[pos+1];
        uint16_t attr_len = (response[pos+2] << 8) | response[pos+3];
        pos += 4;
        if (type == 0x0001 && attr_len >= 8) {
            unsigned char family = response[pos+1];
            if (family == 0x01) {
                uint16_t port = (response[pos+2] << 8) | response[pos+3];
                uint32_t addr = (response[pos+4] << 24) | (response[pos+5] << 16) | (response[pos+6] << 8) | response[pos+7];
                std::string ip = std::to_string((addr >> 24) & 0xFF) + "." + std::to_string((addr >> 16) & 0xFF) + "." + std::to_string((addr >> 8) & 0xFF) + "." + std::to_string(addr & 0xFF);
                return {ip, ntohs(port)};
            }
        }
        pos += attr_len;
        if (attr_len % 4 != 0) pos += 4 - (attr_len % 4);
    }

    return {"", 0};
}
