#include "../include/socket_utils.h"
#include "../include/turn.h"
#include <iostream>

int main(int argc, char** argv) {
    if (argc < 7) {
        std::cerr << "Usage: turn_client <turn_host> <turn_port> <username> <password> <peer_ip> <peer_port>\n";
        return 1;
    }
    std::string turn_host = argv[1];
    uint16_t turn_port = static_cast<uint16_t>(std::stoi(argv[2]));
    std::string username = argv[3];
    std::string password = argv[4];
    std::string peer_ip = argv[5];
    uint16_t peer_port = static_cast<uint16_t>(std::stoi(argv[6]));

    sockets_init();
    TurnAllocation alloc;
    TurnAuthData auth;
    if (!turn_allocate(turn_host, turn_port, username, password, alloc, auth)) {
        std::cerr << "TURN allocate failed\n";
        sockets_cleanup();
        return 1;
    }
    std::cout << "TURN auth realm=" << auth.realm << " nonce=" << auth.nonce << "\n";
    std::cout << "Relay allocation: " << alloc.relay_ip << ":" << alloc.relay_port << "\n";

    if (!turn_create_permission(turn_host, turn_port, username, password, auth, peer_ip, peer_port)) {
        std::cerr << "TURN permission failed\n";
        sockets_cleanup();
        return 1;
    }

    if (!turn_send_data(turn_host, turn_port, username, password, auth, peer_ip, peer_port, "hello from turn_client")) {
        std::cerr << "TURN send failed\n";
        sockets_cleanup();
        return 1;
    }

    sockets_cleanup();
    return 0;
}
