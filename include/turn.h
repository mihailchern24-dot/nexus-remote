#pragma once

#include <string>
#include <utility>
#include <vector>

struct TurnAllocation {
    std::string relay_ip;
    uint16_t relay_port;
};

struct TurnAuthData {
    std::string realm;
    std::string nonce;
};

bool turn_allocate(const std::string &turn_host, uint16_t turn_port,
                   const std::string &username, const std::string &password,
                   TurnAllocation &out_alloc,
                   TurnAuthData &out_auth);

bool turn_create_permission(const std::string &turn_host, uint16_t turn_port,
                            const std::string &username, const std::string &password,
                            const TurnAuthData &auth,
                            const std::string &peer_ip, uint16_t peer_port);

bool turn_send_data(const std::string &turn_host, uint16_t turn_port,
                    const std::string &username, const std::string &password,
                    const TurnAuthData &auth,
                    const std::string &peer_ip, uint16_t peer_port,
                    const std::string &payload);
