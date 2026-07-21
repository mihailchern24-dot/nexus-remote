#include "../include/socket_utils.h"
#include "../include/tls_utils.h"

#include <openssl/ssl.h>
#include <thread>
#include <vector>
#include <iostream>

// Note: minimal TLS relay that is illustrative only. Proper error handling and async I/O required for production.
int main(int argc, char** argv) {
    uint16_t port = 9443;
    if (argc >= 2) port = static_cast<uint16_t>(std::stoi(argv[1]));

    init_openssl();
    SSL_CTX* ctx = create_server_context();
    if (!ctx) return 1;

    sockets_init();
    socket_t listen_sock = create_listen_socket(port);
    if (listen_sock < 0) return 1;

    std::cout << "TLS Relay listening on " << port << "\n";

    while (true) {
        socket_t a = accept_client(listen_sock);
        if (a < 0) continue;
        socket_t b = accept_client(listen_sock);
        if (b < 0) { close_socket(a); continue; }

        std::thread([a,b,ctx]() {
            SSL *ssl_a = SSL_new(ctx);
            SSL_set_fd(ssl_a, (int)a);
            if (SSL_accept(ssl_a) <= 0) {
                SSL_free(ssl_a); close_socket(a); close_socket(b); return;
            }

            SSL *ssl_b = SSL_new(ctx);
            SSL_set_fd(ssl_b, (int)b);
            if (SSL_accept(ssl_b) <= 0) {
                SSL_free(ssl_a); SSL_free(ssl_b); close_socket(a); close_socket(b); return;
            }

            // Now forward between ssl_a and ssl_b (synchronous)
            const int BUF=16384;
            std::vector<char> buf(BUF);
            while (true) {
                int n = SSL_read(ssl_a, buf.data(), BUF);
                if (n <= 0) break;
                int written = 0;
                while (written < n) {
                    int w = SSL_write(ssl_b, buf.data()+written, n-written);
                    if (w <= 0) goto done;
                    written += w;
                }
            }
        done:
            SSL_shutdown(ssl_a); SSL_shutdown(ssl_b);
            SSL_free(ssl_a); SSL_free(ssl_b);
            close_socket(a); close_socket(b);
        }).detach();
    }

    close_socket(listen_sock);
    cleanup_openssl();
    sockets_cleanup();
    return 0;
}
