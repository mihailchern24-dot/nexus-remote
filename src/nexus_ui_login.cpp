// nexus_ui_login.cpp - C++ UI с логин-формой
// омпиляция: g++ -o nexus_ui.exe nexus_ui_login.cpp -lwinhttp -lgdiplus -mwindows
#include <windows.h>
#include <winhttp.h>
#include <string>
#include <thread>

#pragma comment(lib, "winhttp.lib")

// лобальные переменные
static std::string g_token = "";
static std::string g_peer_id = "";
static std::string g_email = "";
static HWND hEmail, hPassword, hLoginBtn, hStatus;

// HTTP запрос к серверу
static std::string http_post(const std::string& path, const std::string& json) {
    std::wstring host = L"nexus-remote.onrender.com";
    std::wstring wpath(path.begin(), path.end());
    
    HINTERNET hSession = WinHttpOpen(L"Nexus Remote/4.0", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, NULL, NULL, 0);
    if (!hSession) return "";
    
    HINTERNET hConnect = WinHttpConnect(hSession, host.c_str(), 443, 0);
    if (!hConnect) { WinHttpCloseHandle(hSession); return ""; }
    
    HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"POST", wpath.c_str(), NULL, NULL, NULL, WINHTTP_FLAG_SECURE);
    if (!hRequest) { WinHttpCloseHandle(hConnect); WinHttpCloseHandle(hSession); return ""; }
    
    std::wstring headers = L"Content-Type: application/json\r\n";
    WinHttpAddRequestHeaders(hRequest, headers.c_str(), -1, WINHTTP_ADDREQ_FLAG_ADD);
    WinHttpSendRequest(hRequest, headers.c_str(), -1, (LPVOID)json.c_str(), json.size(), json.size(), 0);
    WinHttpReceiveResponse(hRequest, NULL);
    
    char buffer[2048];
    DWORD bytesRead;
    std::string response;
    while (WinHttpReadData(hRequest, buffer, sizeof(buffer), &bytesRead) && bytesRead > 0) {
        response.append(buffer, bytesRead);
    }
    
    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);
    return response;
}

// опытка входа
static void do_login(HWND hwnd) {
    char email[256], password[256];
    GetWindowTextA(hEmail, email, 256);
    GetWindowTextA(hPassword, password, 256);
    
    if (strlen(email) == 0 || strlen(password) == 0) {
        SetWindowTextA(hStatus, "Please enter email and password");
        return;
    }
    
    SetWindowTextA(hStatus, "Logging in...");
    
    std::string json = "{\"email\":\"" + std::string(email) + "\",\"password\":\"" + std::string(password) + "\"}";
    std::string response = http_post("/api/auth/login", json);
    
    // ростой парсинг JSON (в реальном приложении использовать библиотеку)
    if (response.find("\"token\":\"") != std::string::npos) {
        size_t token_start = response.find("\"token\":\"") + 9;
        size_t token_end = response.find("\"", token_start);
        g_token = response.substr(token_start, token_end - token_start);
        
        size_t peer_start = response.find("\"peer_id\":\"") + 12;
        size_t peer_end = response.find("\"", peer_start);
        g_peer_id = response.substr(peer_start, peer_end - peer_start);
        
        g_email = email;
        
        SetWindowTextA(hStatus, "Login successful! Starting...");
        MessageBoxA(hwnd, ("Welcome " + g_email + "!\nPeer ID: " + g_peer_id).c_str(), "Nexus Remote", MB_OK | MB_ICONINFORMATION);
        
        // десь запуск основного UI
        // ShowWindow(hwnd, SW_HIDE);
        // CreateMainWindow(g_token, g_peer_id);
    } else {
        SetWindowTextA(hStatus, "Invalid credentials");
    }
}

// конная процедура
LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
        case WM_CREATE: {
            // аголовок
            CreateWindowA("STATIC", "Nexus Remote Login",
                WS_VISIBLE | WS_CHILD | SS_CENTER,
                50, 30, 300, 40, hwnd, NULL, NULL, NULL);
            
            // Email поле
            CreateWindowA("STATIC", "Email:", WS_VISIBLE | WS_CHILD,
                50, 80, 300, 20, hwnd, NULL, NULL, NULL);
            hEmail = CreateWindowA("EDIT", "",
                WS_VISIBLE | WS_CHILD | WS_BORDER | ES_AUTOHSCROLL,
                50, 100, 300, 30, hwnd, NULL, NULL, NULL);
            
            // ароль поле
            CreateWindowA("STATIC", "Password:", WS_VISIBLE | WS_CHILD,
                50, 140, 300, 20, hwnd, NULL, NULL, NULL);
            hPassword = CreateWindowA("EDIT", "",
                WS_VISIBLE | WS_CHILD | WS_BORDER | ES_PASSWORD | ES_AUTOHSCROLL,
                50, 160, 300, 30, hwnd, NULL, NULL, NULL);
            
            // нопка входа
            hLoginBtn = CreateWindowA("BUTTON", "Sign In",
                WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
                50, 210, 300, 40, hwnd, (HMENU)1, NULL, NULL);
            
            // Статус
            hStatus = CreateWindowA("STATIC", "",
                WS_VISIBLE | WS_CHILD | SS_CENTER,
                50, 260, 300, 30, hwnd, NULL, NULL, NULL);
            
            // Ссылки
            CreateWindowA("STATIC", "Forgot password? Visit nexus-remote.onrender.com/reset",
                WS_VISIBLE | WS_CHILD | SS_CENTER,
                50, 300, 300, 20, hwnd, NULL, NULL, NULL);
            
            CreateWindowA("STATIC", "Don't have account? Register on website",
                WS_VISIBLE | WS_CHILD | SS_CENTER,
                50, 320, 300, 20, hwnd, NULL, NULL, NULL);
            
            break;
        }
        case WM_COMMAND:
            if (LOWORD(wParam) == 1) {
                do_login(hwnd);
            }
            break;
        case WM_DESTROY:
            PostQuitMessage(0);
            break;
        default:
            return DefWindowProcA(hwnd, msg, wParam, lParam);
    }
    return 0;
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE, LPSTR, int nCmdShow) {
    const char CLASS_NAME[] = "NexusLoginWindow";
    
    WNDCLASSA wc = {};
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = CLASS_NAME;
    wc.hbrBackground = CreateSolidBrush(RGB(12, 12, 24));
    wc.hCursor = LoadCursorA(NULL, IDC_ARROW);
    
    RegisterClassA(&wc);
    
    HWND hwnd = CreateWindowA(CLASS_NAME, "Nexus Remote v4.0 - Login",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
        CW_USEDEFAULT, CW_USEDEFAULT, 420, 420,
        NULL, NULL, hInstance, NULL);
    
    if (!hwnd) return 0;
    
    ShowWindow(hwnd, nCmdShow);
    UpdateWindow(hwnd);
    
    MSG msg;
    while (GetMessageA(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageA(&msg);
    }
    
    return 0;
}
