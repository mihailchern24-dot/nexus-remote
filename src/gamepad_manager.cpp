#include "../include/gamepad_manager.h"
#include <atomic>

static GamepadManagerConfig g_config;
static std::atomic<bool> g_initialized(false);

bool initialize_gamepad_manager(const GamepadManagerConfig &config) {
    g_config = config;
    g_initialized = true;
    return true;
}

bool should_show_gamepad() {
    if (!g_initialized) return true;
    return is_gamepad_allowed(g_config.filter);
}

std::string get_gamepad_filter_summary() {
    std::string summary;
    if (!g_config.filter.appName.empty()) {
        summary += "app=" + g_config.filter.appName;
    }
    if (!g_config.filter.vendorId.empty()) {
        if (!summary.empty()) summary += ",";
        summary += "vendor=" + g_config.filter.vendorId;
    }
    if (!g_config.filter.productId.empty()) {
        if (!summary.empty()) summary += ",";
        summary += "product=" + g_config.filter.productId;
    }
    return summary.empty() ? "none" : summary;
}
