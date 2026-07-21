#include "../include/input_filter.h"
#ifdef _WIN32
#include <windows.h>
#include <tlhelp32.h>
#endif

#include <algorithm>
#include <vector>
#include <string>

#ifdef _WIN32
#include <wincrypt.h>
#endif

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
        do {
            if (pe.th32ProcessID == pid) {
                activeApp = pe.szExeFile;
                break;
            }
        } while (Process32Next(snap, &pe));
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

static std::wstring widen(const std::string &utf8) {
    if (utf8.empty()) return {};
    int size_needed = MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), (int)utf8.size(), nullptr, 0);
    std::wstring result(size_needed, 0);
    MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), (int)utf8.size(), &result[0], size_needed);
    return result;
}

static std::string narrow(const std::wstring &wstr) {
    if (wstr.empty()) return {};
    int size_needed = WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(), (int)wstr.size(), nullptr, 0, nullptr, nullptr);
    std::string result(size_needed, 0);
    WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(), (int)wstr.size(), &result[0], size_needed, nullptr, nullptr);
    return result;
}

static bool parse_vid_pid(const std::wstring &name, std::string &vendorId, std::string &productId) {
    std::wstring lower = name;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::towlower);
    size_t vid_pos = lower.find(L"vid_");
    size_t pid_pos = lower.find(L"pid_");
    if (vid_pos == std::wstring::npos || pid_pos == std::wstring::npos) return false;
    vendorId = narrow(name.substr(vid_pos + 4, 4));
    productId = narrow(name.substr(pid_pos + 4, 4));
    return true;
}

static bool has_matching_hid_device(const std::string &vendorId, const std::string &productId) {
    if (vendorId.empty() && productId.empty()) return true;
#ifdef _WIN32
    UINT count = 0;
    if (GetRawInputDeviceList(nullptr, &count, sizeof(RAWINPUTDEVICELIST)) != 0 || count == 0) return false;
    std::vector<RAWINPUTDEVICELIST> devices(count);
    if (GetRawInputDeviceList(devices.data(), &count, sizeof(RAWINPUTDEVICELIST)) == (UINT)-1) return false;
    for (UINT i = 0; i < count; ++i) {
        if (devices[i].dwType != RIM_TYPEHID) continue;
        UINT size = 0;
        if (GetRawInputDeviceInfoW(devices[i].hDevice, RIDI_DEVICENAME, nullptr, &size) != 0) continue;
        std::wstring name(size, 0);
        if (GetRawInputDeviceInfoW(devices[i].hDevice, RIDI_DEVICENAME, &name[0], &size) == (UINT)-1) continue;
        name.resize(size - 1);
        std::string vendor, product;
        if (!parse_vid_pid(name, vendor, product)) continue;
        if (!vendorId.empty() && _stricmp(vendor.c_str(), vendorId.c_str()) != 0) continue;
        if (!productId.empty() && _stricmp(product.c_str(), productId.c_str()) != 0) continue;
        return true;
    }
#endif
    return false;
}

bool should_show_gamepad_for_device(const std::string &vendorId, const std::string &productId) {
#ifdef _WIN32
    return has_matching_hid_device(vendorId, productId);
#else
    (void)vendorId;
    (void)productId;
    return true;
#endif
}

bool is_gamepad_allowed(const GamepadFilterConfig &config) {
    if (!config.appName.empty() && !should_show_gamepad_for_app(config.appName)) return false;
    if (!config.vendorId.empty() || !config.productId.empty()) {
        if (!should_show_gamepad_for_device(config.vendorId, config.productId)) return false;
    }
    return true;
}
