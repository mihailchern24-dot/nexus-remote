#include "../include/socket_utils.h"

#include <iostream>
#include <thread>
#include <vector>
#include "../include/crypto_utils.h"

void recv_loop(socket_t s, const std::string &key_hex) {
    std::string buffer;
    const size_t BUF_SIZE = 16 * 1024;
    std::vector<char> buf(BUF_SIZE);
    while (true) {
        int n = recv(s, buf.data(), (int)buf.size(), 0);
        if (n <= 0) break;
        buffer.append(buf.data(), n);
        // process lines
        size_t pos;
        while ((pos = buffer.find('\n')) != std::string::npos) {
            std::string line = buffer.substr(0, pos);
            buffer.erase(0, pos+1);
            if (!key_hex.empty()) {
                std::string plain;
                if (aes_gcm_decrypt(key_hex, line, plain)) {
                    std::cout << plain;
                } else {
                    // not decryptable, print raw
                    std::cout << line << "\n";
                }
            } else {
                std::cout << line << "\n";
            }
            std::cout.flush();
        }
    }
}

int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "Usage: client <host> <port>\n";
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

    // optional key argument via env or later CLI extension
    std::string key_hex;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if ((a == "-k" || a == "--key") && i + 1 < argc) { key_hex = argv[i+1]; }
    }

    std::thread reader(recv_loop, s, key_hex);

    std::string line;
    while (std::getline(std::cin, line)) {
        line.push_back('\n');
        std::string outdata = line;
        if (!key_hex.empty()) {
            std::string cipher_hex;
            if (aes_gcm_encrypt(key_hex, line, cipher_hex)) {
                outdata = cipher_hex + "\n";
            } else {
                std::cerr << "Encryption failed\n";
            }
        }
        send(s, outdata.data(), (int)outdata.size(), 0);
    }

    shutdown(s, 2);
    reader.join();
    close_socket(s);
    sockets_cleanup();
    return 0;
}
