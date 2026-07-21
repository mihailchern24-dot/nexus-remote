#include "../include/socket_utils.h"
#include "../include/stun.h"

#include <iostream>

int main(int argc, char** argv) {
    std::string server = "stun.l.google.com";
    uint16_t port = 19302;
    if (argc >= 2) server = argv[1];
    if (argc >= 3) port = static_cast<uint16_t>(std::stoi(argv[2]));

    sockets_init();
    auto endpoint = stun_get_public_endpoint(server, port);
    if (endpoint.second == 0) {
        std::cerr << "STUN request failed\n";
        return 1;
    }

    std::cout << "Public endpoint: " << endpoint.first << ":" << endpoint.second << "\n";
    sockets_cleanup();
    return 0;
}
