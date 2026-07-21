#include "../include/crypto_utils.h"
#include <string>

bool aes_gcm_encrypt(const std::string &key_hex, const std::string &plaintext, std::string &out_cipher_hex) {
    (void)key_hex; (void)plaintext; (void)out_cipher_hex;
    return false;
}

bool aes_gcm_decrypt(const std::string &key_hex, const std::string &cipher_hex, std::string &out_plaintext) {
    (void)key_hex; (void)cipher_hex; (void)out_plaintext;
    return false;
}
