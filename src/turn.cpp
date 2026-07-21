#include "../include/turn.h"
#include "../include/socket_utils.h"
#include <cstring>
#include <random>
#include <sstream>
#include <vector>
#include <iostream>

// Stub: OpenSSL not available for HMAC
static std::vector<unsigned char> random_bytes(size_t count) {
    static std::mt19937 rng((uint32_t)std::random_device{}());
    std::vector<unsigned char> out(count);
    for (size_t i = 0; i < count; ++i) out[i] = (unsigned char)(rng() & 0xFF);
    return out;
}

bool turn_allocate(const std::string &turn_host, uint16_t turn_port,
                   const std::string &username, const std::string &password,
                   TurnAllocation &out_alloc, TurnAuthData &out_auth) {
    std::cerr << "[TURN] OpenSSL not available, TURN disabled\n";
    return false;
}

bool turn_create_permission(const std::string &turn_host, uint16_t turn_port,
                            const std::string &username, const std::string &password,
                            const TurnAuthData &auth,
                            const std::string &peer_ip, uint16_t peer_port) {
    return false;
}

bool turn_send_data(const std::string &turn_host, uint16_t turn_port,
                    const std::string &username, const std::string &password,
                    const TurnAuthData &auth,
                    const std::string &peer_ip, uint16_t peer_port,
                    const std::string &payload) {
    return false;
}
