#pragma once

#include "input_filter.h"
#include <string>

struct GamepadManagerConfig {
    GamepadFilterConfig filter;
};

bool initialize_gamepad_manager(const GamepadManagerConfig &config);
bool should_show_gamepad();
std::string get_gamepad_filter_summary();
