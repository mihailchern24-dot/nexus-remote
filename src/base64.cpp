#include <cstring>
#include "../include/base64.h"

static const char* BASE64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

std::string base64_encode(const std::vector<unsigned char> &data) {
    std::string out;
    out.reserve(((data.size() + 2) / 3) * 4);
    size_t i = 0;

    while (i + 2 < data.size()) {
        unsigned int val = (data[i] << 16) | (data[i+1] << 8) | data[i+2];
        out.push_back(BASE64_CHARS[(val >> 18) & 0x3F]);
        out.push_back(BASE64_CHARS[(val >> 12) & 0x3F]);
        out.push_back(BASE64_CHARS[(val >> 6) & 0x3F]);
        out.push_back(BASE64_CHARS[val & 0x3F]);
        i += 3;
    }

    if (i < data.size()) {
        unsigned int val = data[i] << 16;
        out.push_back(BASE64_CHARS[(val >> 18) & 0x3F]);
        if (i + 1 < data.size()) {
            val |= data[i+1] << 8;
            out.push_back(BASE64_CHARS[(val >> 12) & 0x3F]);
            out.push_back(BASE64_CHARS[(val >> 6) & 0x3F]);
            out.push_back('=');
        } else {
            out.push_back(BASE64_CHARS[(val >> 12) & 0x3F]);
            out.push_back('=');
            out.push_back('=');
        }
    }

    return out;
}

static inline bool is_base64(unsigned char c) {
    return (std::isalnum(c) || c == '+' || c == '/');
}

std::vector<unsigned char> base64_decode(const std::string &input) {
    std::vector<unsigned char> out;
    int val = 0, valb = -8;
    for (unsigned char c : input) {
        if (std::isspace(c) || c == '=') break;
        if (!is_base64(c)) continue;
        val = (val << 6) + (strchr(BASE64_CHARS, c) - BASE64_CHARS);
        valb += 6;
        if (valb >= 0) {
            out.push_back((unsigned char)((val >> valb) & 0xFF));
            valb -= 8;
        }
    }
    return out;
}

