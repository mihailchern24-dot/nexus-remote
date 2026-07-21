#pragma once

#include <string>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
using socket_t = SOCKET;
#else
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
using socket_t = int;
#endif

void sockets_init();
void sockets_cleanup();
socket_t create_listen_socket(uint16_t port);
socket_t accept_client(socket_t listen_sock);
socket_t connect_to_host(const std::string &host, uint16_t port);
void close_socket(socket_t sock);
