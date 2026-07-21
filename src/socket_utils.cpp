#include "../include/socket_utils.h"

#include <cstring>
#include <iostream>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
#else
#include <unistd.h>
#include <fcntl.h>
#endif

void sockets_init() {
#ifdef _WIN32
    WSADATA wsaData;
    int res = WSAStartup(MAKEWORD(2,2), &wsaData);
    if (res != 0) {
        std::cerr << "WSAStartup failed: " << res << "\n";
    }
#endif
}

void sockets_cleanup() {
#ifdef _WIN32
    WSACleanup();
#endif
}

socket_t create_listen_socket(uint16_t port) {
    socket_t listen_sock = ::socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listen_sock < 0) return -1;

    int opt = 1;
    setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR,
#ifdef _WIN32
               (const char*)&opt,
#else
               &opt,
#endif
               sizeof(opt));

    struct sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port);

    if (bind(listen_sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        close_socket(listen_sock);
        return -1;
    }

    if (listen(listen_sock, 16) < 0) {
        close_socket(listen_sock);
        return -1;
    }

    return listen_sock;
}

socket_t accept_client(socket_t listen_sock) {
    struct sockaddr_in client_addr{};
    socklen_t addrlen = sizeof(client_addr);
    socket_t s = ::accept(listen_sock, (struct sockaddr*)&client_addr, &addrlen);
    return s;
}

socket_t connect_to_host(const std::string &host, uint16_t port) {
    struct addrinfo hints{}, *res = nullptr;
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;

    std::string portstr = std::to_string(port);
    int rc = getaddrinfo(host.c_str(), portstr.c_str(), &hints, &res);
    if (rc != 0 || !res) return -1;

    socket_t s = ::socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (s < 0) { freeaddrinfo(res); return -1; }

    if (::connect(s, res->ai_addr, (int)res->ai_addrlen) != 0) {
        close_socket(s);
        freeaddrinfo(res);
        return -1;
    }

    freeaddrinfo(res);
    return s;
}

void close_socket(socket_t sock) {
#ifdef _WIN32
    closesocket(sock);
#else
    ::close(sock);
#endif
}
