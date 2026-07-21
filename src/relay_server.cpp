#include "../include/socket_utils.h"

#include <thread>
#include <vector>
#include <iostream>

void forward_data(socket_t a, socket_t b) {
    const size_t BUF_SIZE = 16 * 1024;
    std::vector<char> buf(BUF_SIZE);
    while (true) {
        int n = recv(a, buf.data(), (int)buf.size(), 0);
        if (n <= 0) break;
        int sent = 0;
        while (sent < n) {
            int s = send(b, buf.data() + sent, n - sent, 0);
            if (s <= 0) goto done;
            sent += s;
        }
    }
done:
    shutdown(a, 2);
    shutdown(b, 2);
}

int main(int argc, char** argv) {
    uint16_t port = 9000;
    if (argc >= 2) port = static_cast<uint16_t>(std::stoi(argv[1]));

    sockets_init();

    socket_t listen_sock = create_listen_socket(port);
    if (listen_sock < 0) {
        std::cerr << "Failed to create listen socket on port " << port << "\n";
        return 1;
    }

    std::cout << "Relay server listening on port " << port << "\n";

    while (true) {
        std::cout << "Waiting for peer A...\n";
        socket_t a = accept_client(listen_sock);
        if (a < 0) continue;
        std::cout << "Peer A connected. Waiting for peer B...\n";
        socket_t b = accept_client(listen_sock);
        if (b < 0) {
            close_socket(a);
            continue;
        }

        std::cout << "Pair connected. Starting forward threads.\n";

        std::thread t1(forward_data, a, b);
        std::thread t2(forward_data, b, a);
        t1.detach();
        t2.detach();
    }

    close_socket(listen_sock);
    sockets_cleanup();
    return 0;
}
