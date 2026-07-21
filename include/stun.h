#pragma once

#include <string>
#include <utility>

std::pair<std::string, uint16_t> stun_get_public_endpoint(const std::string &server_host, uint16_t server_port);
