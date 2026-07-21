#pragma once

#include <string>

std::string make_websocket_accept(const std::string &key);
std::string build_websocket_frame(const std::string &payload, bool mask = false);
std::string read_websocket_payload(const std::string &frame);
