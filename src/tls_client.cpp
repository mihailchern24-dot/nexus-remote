#include "../include/socket_utils.h"
#include "../include/tls_utils.h"

#include <openssl/err.h>
#include <iostream>

int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "Usage: tls_client <host> <port>\n";
        return 1;
    }
    std::string host = argv[1];
    uint16_t port = static_cast<uint16_t>(std::stoi(argv[2]));

    sockets_init();
    socket_t s = connect_to_host(host, port);
    if (s < 0) {
        std::cerr << "Failed to connect to " << host << ":" << port << "\n";
        return 1;
    }

    init_openssl();
    SSL_CTX* ctx = create_client_context();
    if (!ctx) return 1;

    SSL* ssl = SSL_new(ctx);
    SSL_set_fd(ssl, (int)s);
    if (SSL_connect(ssl) <= 0) {
        std::cerr << "TLS handshake failed\n";
        ERR_print_errors_fp(stderr);
        SSL_free(ssl);
        sockets_cleanup();
        return 1;
    }

    std::cout << "Connected to TLS server\n";
    std::string line;
    while (std::getline(std::cin, line)) {
        line.push_back('\n');
        SSL_write(ssl, line.c_str(), (int)line.size());
        char buf[4096];
        int n = SSL_read(ssl, buf, sizeof(buf));
        if (n <= 0) break;
        std::cout.write(buf, n);
        std::cout.flush();
    }

    SSL_shutdown(ssl);
    SSL_free(ssl);
    cleanup_openssl();
    close_socket(s);
    sockets_cleanup();
    return 0;
}
