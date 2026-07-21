#include "../include/sha1.h"
#include <cstring>

static inline uint32_t rotate_left(uint32_t value, unsigned int count) {
    return (value << count) | (value >> (32 - count));
}

static void process_block(const unsigned char block[64], uint32_t state[5]) {
    uint32_t w[80];
    for (int i = 0; i < 16; ++i) {
        w[i] = (uint32_t)block[4*i] << 24 | (uint32_t)block[4*i+1] << 16 | (uint32_t)block[4*i+2] << 8 | (uint32_t)block[4*i+3];
    }
    for (int i = 16; i < 80; ++i) {
        w[i] = rotate_left(w[i-3] ^ w[i-8] ^ w[i-14] ^ w[i-16], 1);
    }

    uint32_t a = state[0];
    uint32_t b = state[1];
    uint32_t c = state[2];
    uint32_t d = state[3];
    uint32_t e = state[4];

    for (int i = 0; i < 80; ++i) {
        uint32_t f, k;
        if (i < 20) {
            f = (b & c) | ((~b) & d);
            k = 0x5A827999;
        } else if (i < 40) {
            f = b ^ c ^ d;
            k = 0x6ED9EBA1;
        } else if (i < 60) {
            f = (b & c) | (b & d) | (c & d);
            k = 0x8F1BBCDC;
        } else {
            f = b ^ c ^ d;
            k = 0xCA62C1D6;
        }
        uint32_t temp = rotate_left(a, 5) + f + e + k + w[i];
        e = d;
        d = c;
        c = rotate_left(b, 30);
        b = a;
        a = temp;
    }

    state[0] += a;
    state[1] += b;
    state[2] += c;
    state[3] += d;
    state[4] += e;
}

static std::array<unsigned char, 20> sha1_internal(const unsigned char *data, size_t len) {
    uint32_t state[5] = {
        0x67452301,
        0xEFCDAB89,
        0x98BADCFE,
        0x10325476,
        0xC3D2E1F0
    };

    uint64_t bitlen = len * 8;
    size_t rem = len % 64;
    size_t padded_len = len + 1 + ((rem < 56) ? (56 - rem) : (120 - rem)) + 8;
    std::vector<unsigned char> padded(padded_len);
    std::memcpy(padded.data(), data, len);
    padded[len] = 0x80;
    for (size_t i = len + 1; i < padded_len - 8; ++i) padded[i] = 0;
    for (int i = 0; i < 8; ++i) padded[padded_len - 1 - i] = (unsigned char)((bitlen >> (8 * i)) & 0xFF);

    for (size_t i = 0; i < padded_len; i += 64) {
        process_block(padded.data() + i, state);
    }

    std::array<unsigned char, 20> digest;
    for (int i = 0; i < 5; ++i) {
        digest[4*i] = (unsigned char)((state[i] >> 24) & 0xFF);
        digest[4*i+1] = (unsigned char)((state[i] >> 16) & 0xFF);
        digest[4*i+2] = (unsigned char)((state[i] >> 8) & 0xFF);
        digest[4*i+3] = (unsigned char)(state[i] & 0xFF);
    }
    return digest;
}

std::array<unsigned char, 20> sha1(const std::vector<unsigned char> &data) {
    return sha1_internal(data.data(), data.size());
}

std::array<unsigned char, 20> sha1(const std::string &text) {
    return sha1_internal((const unsigned char*)text.data(), text.size());
}
