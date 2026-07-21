#pragma once

#include <string>

bool aes_gcm_encrypt(const std::string &key_hex, const std::string &plaintext, std::string &out_cipher_hex);
bool aes_gcm_decrypt(const std::string &key_hex, const std::string &cipher_hex, std::string &out_plaintext);
