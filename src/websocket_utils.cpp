#include "../include/websocket_utils.h"
#include "../include/base64.h"
#include "../include/sha1.h"
#include <sstream>
#include <iomanip>
#include <cstring>

static std::string to_hex(const std::array<unsigned char, 20> &digest) {
    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    for (auto b : digest) oss << std::setw(2) << (int)b;
    return oss.str();
}

static std::string sha1_base64(const std::string &input) {
    auto digest = sha1(input);
    std::vector<unsigned char> digest_vec(digest.begin(), digest.end());
    return base64_encode(digest_vec);
}

std::string make_websocket_accept(const std::string &key) {
    static const std::string magic = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
    return sha1_base64(key + magic);
}

std::string build_websocket_frame(const std::string &payload, bool mask) {
    std::string frame;
    frame.push_back((char)0x81);
    size_t len = payload.size();
    unsigned char mask_byte = mask ? 0x80 : 0x00;
    if (len <= 125) {
        frame.push_back((char)(mask_byte | (unsigned char)len));
    } else if (len <= 65535) {
        frame.push_back((char)(mask_byte | 126));
        frame.push_back((char)((len >> 8) & 0xFF));
        frame.push_back((char)(len & 0xFF));
    } else {
        frame.push_back((char)(mask_byte | 127));
        for (int i = 7; i >= 0; --i) frame.push_back((char)((len >> (8 * i)) & 0xFF));
    }
    if (mask) {
        unsigned char masking_key[4] = {0};
        for (int i = 0; i < 4; ++i) masking_key[i] = (unsigned char)(rand() & 0xFF);
        frame.append((char*)masking_key, 4);
        for (size_t i = 0; i < len; ++i) {
            frame.push_back(payload[i] ^ masking_key[i % 4]);
        }
    } else {
        frame.append(payload);
    }
    return frame;
}

std::string read_websocket_payload(const std::string &frame) {
    if (frame.size() < 2) return {};
    size_t pos = 1;
    unsigned char second = frame[pos++];
    size_t length = second & 0x7F;
    if (length == 126) {
        if (frame.size() < pos + 2) return {};
        length = ((unsigned char)frame[pos] << 8) | (unsigned char)frame[pos+1];
        pos += 2;
    } else if (length == 127) {
        if (frame.size() < pos + 8) return {};
        length = 0;
        for (int i = 0; i < 8; ++i) length = (length << 8) | (unsigned char)frame[pos++];
    }
    if (second & 0x80) {
        if (frame.size() < pos + 4) return {};
        unsigned char mask[4] = { (unsigned char)frame[pos], (unsigned char)frame[pos+1], (unsigned char)frame[pos+2], (unsigned char)frame[pos+3] };
        pos += 4;
        if (frame.size() < pos + length) return {};
        std::string payload;
        payload.resize(length);
        for (size_t i = 0; i < length; ++i) {
            payload[i] = frame[pos + i] ^ mask[i % 4];
        }
        return payload;
    }
    if (frame.size() < pos + length) return {};
    return frame.substr(pos, length);
}
