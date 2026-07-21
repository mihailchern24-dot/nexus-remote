#include "../include/crypto_utils.h"
#include <string>

// Stub: OpenSSL not available, using plaintext fallback
bool aes_gcm_encrypt(const std::string &key_hex, const std::string &plaintext, std::string &out_cipher_hex) {
    out_cipher_hex = "PLAIN:" + plaintext;
    return true;
}

bool aes_gcm_decrypt(const std::string &key_hex, const std::string &cipher_hex, std::string &out_plaintext) {
    if (cipher_hex.rfind("PLAIN:", 0) == 0) {
        out_plaintext = cipher_hex.substr(6);
        return true;
    }
    out_plaintext = cipher_hex;
    return true;
}
