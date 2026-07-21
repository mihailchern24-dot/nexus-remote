#pragma once

#include <string>

struct GamepadFilterConfig {
    std::string appName;
    std::string vendorId;
    std::string productId;
};

bool should_show_gamepad_for_app(const std::string &appName);
bool should_show_gamepad_for_device(const std::string &vendorId, const std::string &productId);
bool is_gamepad_allowed(const GamepadFilterConfig &config);
