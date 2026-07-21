#include "../include/input_filter.h"
#ifdef _WIN32
#include <windows.h>
#include <tlhelp32.h>
#include <wincrypt.h>
#endif
#include <algorithm>
#include <vector>
#include <string>
#include <cctype>

bool should_show_gamepad_for_app(const std::string &appName) {
#ifdef _WIN32
    std::string activeApp;
    HWND foreground = GetForegroundWindow();
    if (!foreground) return false;
    DWORD pid = 0;
    GetWindowThreadProcessId(foreground, &pid);
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snap == INVALID_HANDLE_VALUE) return false;
    PROCESSENTRY32 pe{};
    pe.dwSize = sizeof(pe);
    if (Process32First(snap, &pe)) {
        do { if (pe.th32ProcessID == pid) { activeApp = pe.szExeFile; break; } }
        while (Process32Next(snap, &pe));
    }
    CloseHandle(snap);
    if (activeApp.empty()) return false;
    std::string lowerActive = activeApp;
    std::transform(lowerActive.begin(), lowerActive.end(), lowerActive.begin(), ::tolower);
    std::string lowerTarget = appName;
    std::transform(lowerTarget.begin(), lowerTarget.end(), lowerTarget.begin(), ::tolower);
    return lowerActive.find(lowerTarget) != std::string::npos;
#else
    (void)appName;
    return false;
#endif
}

bool should_show_gamepad_for_device(const std::string &vendorId, const std::string &productId) {
    (void)vendorId; (void)productId;
    return true;
}

bool is_gamepad_allowed(const GamepadFilterConfig &config) {
    if (!config.appName.empty() && !should_show_gamepad_for_app(config.appName)) return false;
    if (!config.vendorId.empty() || !config.productId.empty()) {
        if (!should_show_gamepad_for_device(config.vendorId, config.productId)) return false;
    }
    return true;
}
