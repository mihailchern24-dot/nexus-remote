// nexus_modern_ui.cpp - Modern C++ UI with Login + WOL + Streaming
// Compile: g++ -o NexusRemote.exe nexus_modern_ui.cpp -lwinhttp -lgdiplus -lws2_32 -mwindows
#include <windows.h>
#include <winhttp.h>
#include <gdiplus.h>
#include <string>
#include <thread>
#include <vector>
#include <map>

#pragma comment(lib, "winhttp.lib")
#pragma comment(lib, "gdiplus.lib")
#pragma comment(lib, "ws2_32.lib")

using namespace Gdiplus;

// ==================== GLOBALS ====================
static std::string g_token = "";
static std::string g_peer_id = "";
static std::string g_email = "";
static std::string g_server = "nexus-remote.onrender.com";
static bool g_logged_in = false;
static bool g_streaming = false;
static HWND hMainWnd = nullptr;
static HWND hEmail, hPassword, hLoginBtn, hStatus;
static HWND hPeerInput, hConnectBtn, hStreamBtn, hWolBtn, hWolMac;

// Colors
static Color bg(10, 10, 26);
static Color card(21, 21, 48);
static Color accent(99, 102, 241);
static Color green(34, 197, 94);
static Color red(239, 68, 68);
static Color orange(245, 158, 11);
static Color text(224, 224, 224);
static Color gray(136, 136, 160);
static Color white(255, 255, 255);

// ==================== HTTP CLIENT ====================
static std::string HttpPost(const std::string& path, const std::string& json) {
    std::wstring host(g_server.begin(), g_server.end());
    std::wstring wpath(path.begin(), path.end());
    
    HINTERNET hSession = WinHttpOpen(L"Nexus/4.0", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, NULL, NULL, 0);
    if (!hSession) return "";
    
    HINTERNET hConnect = WinHttpConnect(hSession, host.c_str(), 443, 0);
    if (!hConnect) { WinHttpCloseHandle(hSession); return ""; }
    
    HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"POST", wpath.c_str(), NULL, NULL, NULL, WINHTTP_FLAG_SECURE);
    if (!hRequest) { WinHttpCloseHandle(hConnect); WinHttpCloseHandle(hSession); return ""; }
    
    std::wstring headers = L"Content-Type: application/json\r\n";
    WinHttpAddRequestHeaders(hRequest, headers.c_str(), -1, WINHTTP_ADDREQ_FLAG_ADD);
    WinHttpSendRequest(hRequest, headers.c_str(), -1, (LPVOID)json.c_str(), json.size(), json.size(), 0);
    WinHttpReceiveResponse(hRequest, NULL);
    
    char buf[4096]; DWORD read; std::string resp;
    while (WinHttpReadData(hRequest, buf, sizeof(buf), &read) && read > 0)
        resp.append(buf, read);
    
    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);
    return resp;
}

static std::string HttpGet(const std::string& path) {
    std::wstring host(g_server.begin(), g_server.end());
    std::wstring wpath(path.begin(), path.end());
    
    HINTERNET hSession = WinHttpOpen(L"Nexus/4.0", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, NULL, NULL, 0);
    if (!hSession) return "";
    
    HINTERNET hConnect = WinHttpConnect(hSession, host.c_str(), 443, 0);
    if (!hConnect) { WinHttpCloseHandle(hSession); return ""; }
    
    HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"GET", wpath.c_str(), NULL, NULL, NULL, WINHTTP_FLAG_SECURE);
    if (!hRequest) { WinHttpCloseHandle(hConnect); WinHttpCloseHandle(hSession); return ""; }
    
    WinHttpSendRequest(hRequest, NULL, 0, NULL, 0, 0, 0);
    WinHttpReceiveResponse(hRequest, NULL);
    
    char buf[4096]; DWORD read; std::string resp;
    while (WinHttpReadData(hRequest, buf, sizeof(buf), &read) && read > 0)
        resp.append(buf, read);
    
    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);
    return resp;
}

// ==================== WOL ====================
static bool SendWOL(const std::string& mac) {
    // Parse MAC address
    std::string clean;
    for (char c : mac) if (c != ':' && c != '-' && c != ' ') clean += c;
    if (clean.size() != 12) return false;
    
    // Build magic packet: 6 bytes FF + 16x MAC
    unsigned char packet[102];
    memset(packet, 0xFF, 6);
    for (int i = 0; i < 16; i++) {
        for (int j = 0; j < 6; j++) {
            char byteStr[3] = {clean[j*2], clean[j*2+1], 0};
            packet[6 + i*6 + j] = (unsigned char)strtol(byteStr, NULL, 16);
        }
    }
    
    // Send via UDP broadcast
    SOCKET sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == INVALID_SOCKET) return false;
    
    BOOL broadcast = TRUE;
    setsockopt(sock, SOL_SOCKET, SO_BROADCAST, (char*)&broadcast, sizeof(broadcast));
    
    sockaddr_in addr = {};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(9);
    addr.sin_addr.s_addr = inet_addr("255.255.255.255");
    
    sendto(sock, (char*)packet, sizeof(packet), 0, (sockaddr*)&addr, sizeof(addr));
    closesocket(sock);
    return true;
}

// ==================== LOGIN ====================
static void DoLogin(HWND hwnd) {
    char email[256], password[256];
    GetWindowTextA(hEmail, email, 256);
    GetWindowTextA(hPassword, password, 256);
    
    if (strlen(email) == 0 || strlen(password) == 0) {
        SetWindowTextA(hStatus, "Enter email and password");
        return;
    }
    
    SetWindowTextA(hStatus, "Logging in...");
    
    std::string json = "{\"email\":\"" + std::string(email) + "\",\"password\":\"" + std::string(password) + "\"}";
    std::string resp = HttpPost("/api/auth/login", json);
    
    if (resp.find("\"token\":\"") != std::string::npos) {
        size_t t1 = resp.find("\"token\":\"") + 9;
        size_t t2 = resp.find("\"", t1);
        g_token = resp.substr(t1, t2 - t1);
        
        size_t p1 = resp.find("\"peer_id\":\"") + 12;
        size_t p2 = resp.find("\"", p1);
        g_peer_id = resp.substr(p1, p2 - p1);
        
        g_email = email;
        g_logged_in = true;
        
        SetWindowTextA(hStatus, "Login successful!");
        InvalidateRect(hwnd, NULL, TRUE);
        MessageBoxA(hwnd, ("Welcome " + g_email + "!\nPeer: " + g_peer_id).c_str(), "Nexus Remote", MB_OK | MB_ICONINFORMATION);
    } else {
        SetWindowTextA(hStatus, "Invalid credentials");
    }
}

// ==================== STREAMING ====================
static void StartStream() {
    char peer[256];
    GetWindowTextA(hPeerInput, peer, 256);
    
    if (strlen(peer) == 0) {
        MessageBoxA(hMainWnd, "Enter Peer ID", "Error", MB_OK);
        return;
    }
    
    std::string json = "{\"source\":\"" + g_peer_id + "\",\"target\":\"" + std::string(peer) + "\",\"quality\":\"high\"}";
    std::string resp = HttpPost("/start_stream", json);
    
    if (resp.find("\"streaming\"") != std::string::npos) {
        g_streaming = true;
        SetWindowTextA(hStreamBtn, "Stop Stream");
        MessageBoxA(hMainWnd, "Stream started!", "Nexus Remote", MB_OK);
    } else {
        MessageBoxA(hMainWnd, "Failed to start stream", "Error", MB_OK);
    }
}

static void StopStream() {
    g_streaming = false;
    SetWindowTextA(hStreamBtn, "Start Stream");
    HttpPost("/stop_stream", "{}");
}

// ==================== PAINT ====================
static void DrawLoginScreen(HDC hdc, RECT& rc) {
    Graphics g(hdc);
    g.SetSmoothingMode(SmoothingModeAntiAlias);
    
    // Background
    SolidBrush bgBr(bg);
    g.FillRectangle(&bgBr, 0, 0, rc.right, rc.bottom);
    
    // Title
    Font titleFont(L"Segoe UI", 28, FontStyleBold);
    SolidBrush accentBr(accent);
    g.DrawString(L"Nexus Remote", -1, &titleFont, PointF(50, 50), &accentBr);
    
    Font subtitleFont(L"Segoe UI", 12);
    SolidBrush grayBr(gray);
    g.DrawString(L"Sign in to your account", -1, &subtitleFont, PointF(50, 85), &grayBr);
}

static void DrawMainScreen(HDC hdc, RECT& rc) {
    Graphics g(hdc);
    g.SetSmoothingMode(SmoothingModeAntiAlias);
    
    // Background
    SolidBrush bgBr(bg);
    g.FillRectangle(&bgBr, 0, 0, rc.right, rc.bottom);
    
    // Top bar
    SolidBrush topBr(Color(13, 13, 36));
    g.FillRectangle(&topBr, 0, 0, rc.right, 50);
    
    Font titleFont(L"Segoe UI", 16, FontStyleBold);
    SolidBrush accentBr(accent);
    g.DrawString(L"Nexus Remote", -1, &titleFont, PointF(20, 12), &accentBr);
    
    Font smallFont(L"Segoe UI", 9);
    SolidBrush greenBr(green);
    std::wstring wemail(g_email.begin(), g_email.end());
    g.DrawString((L"Logged in as: " + wemail).c_str(), -1, &smallFont, PointF(200, 18), &greenBr);
    
    // Cards
    int cardX = 20, cardY = 70, cardW = rc.right - 40, cardH = 140;
    
    // Connection card
    SolidBrush cardBr(card);
    g.FillRectangle(&cardBr, cardX, cardY, cardW, cardH);
    
    Font h2Font(L"Segoe UI", 14, FontStyleBold);
    g.DrawString(L"Connect to Device", -1, &h2Font, PointF(40, cardY + 20), &accentBr);
    
    Font infoFont(L"Segoe UI", 10);
    std::wstring wpeer(g_peer_id.begin(), g_peer_id.end());
    g.DrawString((L"Your Peer ID: " + wpeer).c_str(), -1, &infoFont, PointF(40, cardY + 50), &grayBr);
    
    // Stream card
    int card2Y = cardY + cardH + 20;
    SolidBrush card2Br(card);
    g.FillRectangle(&card2Br, cardX, card2Y, cardW, 120);
    
    g.DrawString(L"Streaming", -1, &h2Font, PointF(40, card2Y + 20), &accentBr);
    
    std::string streamStatus = g_streaming ? "Active" : "Inactive";
    Color statusColor = g_streaming ? green : gray;
    SolidBrush statusBr(statusColor);
    std::wstring wstatus(streamStatus.begin(), streamStatus.end());
    g.DrawString((L"Status: " + wstatus).c_str(), -1, &infoFont, PointF(40, card2Y + 50), &statusBr);
    
    // WOL card
    int card3Y = card2Y + 140;
    SolidBrush card3Br(card);
    g.FillRectangle(&card3Br, cardX, card3Y, cardW, 100);
    
    g.DrawString(L"Wake-on-LAN", -1, &h2Font, PointF(40, card3Y + 20), &accentBr);
    g.DrawString(L"Enter MAC address to wake device remotely", -1, &infoFont, PointF(40, card3Y + 50), &grayBr);
}

// ==================== WINDOW PROC ====================
LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    static RECT rc;
    GetClientRect(hwnd, &rc);
    
    switch (msg) {
        case WM_CREATE:
            hMainWnd = hwnd;
            
            if (!g_logged_in) {
                // Login screen
                CreateWindowA("STATIC", "Email:", WS_VISIBLE | WS_CHILD,
                    50, 120, 300, 20, hwnd, NULL, NULL, NULL);
                hEmail = CreateWindowA("EDIT", "", WS_VISIBLE | WS_CHILD | WS_BORDER | ES_AUTOHSCROLL,
                    50, 140, 300, 30, hwnd, NULL, NULL, NULL);
                
                CreateWindowA("STATIC", "Password:", WS_VISIBLE | WS_CHILD,
                    50, 180, 300, 20, hwnd, NULL, NULL, NULL);
                hPassword = CreateWindowA("EDIT", "", WS_VISIBLE | WS_CHILD | WS_BORDER | ES_PASSWORD,
                    50, 200, 300, 30, hwnd, NULL, NULL, NULL);
                
                hLoginBtn = CreateWindowA("BUTTON", "Sign In", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
                    50, 250, 300, 40, hwnd, (HMENU)1, NULL, NULL);
                
                hStatus = CreateWindowA("STATIC", "", WS_VISIBLE | WS_CHILD | SS_CENTER,
                    50, 300, 300, 30, hwnd, NULL, NULL, NULL);
                
                CreateWindowA("STATIC", "Don't have account? Register on nexus-remote.onrender.com",
                    WS_VISIBLE | WS_CHILD | SS_CENTER, 50, 340, 300, 30, hwnd, NULL, NULL, NULL);
            } else {
                // Main screen
                int y = 80;
                CreateWindowA("STATIC", "Peer ID:", WS_VISIBLE | WS_CHILD,
                    40, y, 300, 20, hwnd, NULL, NULL, NULL);
                hPeerInput = CreateWindowA("EDIT", "", WS_VISIBLE | WS_CHILD | WS_BORDER,
                    40, y+22, 250, 30, hwnd, NULL, NULL, NULL);
                
                hConnectBtn = CreateWindowA("BUTTON", "Connect", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
                    300, y+22, 90, 30, hwnd, (HMENU)2, NULL, NULL);
                
                y += 80;
                hStreamBtn = CreateWindowA("BUTTON", "Start Stream", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
                    40, y, 350, 40, hwnd, (HMENU)3, NULL, NULL);
                
                y += 60;
                CreateWindowA("STATIC", "Wake-on-LAN (MAC):", WS_VISIBLE | WS_CHILD,
                    40, y, 350, 20, hwnd, NULL, NULL, NULL);
                hWolMac = CreateWindowA("EDIT", "AA:BB:CC:DD:EE:FF", WS_VISIBLE | WS_CHILD | WS_BORDER,
                    40, y+22, 250, 30, hwnd, NULL, NULL, NULL);
                hWolBtn = CreateWindowA("BUTTON", "Wake Up", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
                    300, y+22, 90, 30, hwnd, (HMENU)4, NULL, NULL);
                
                CreateWindowA("BUTTON", "Logout", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
                    rc.right - 120, 10, 100, 30, hwnd, (HMENU)5, NULL, NULL);
            }
            break;
        
        case WM_COMMAND:
            if (LOWORD(wp) == 1) DoLogin(hwnd);
            else if (LOWORD(wp) == 2) StartStream();
            else if (LOWORD(wp) == 3) { if (g_streaming) StopStream(); else StartStream(); }
            else if (LOWORD(wp) == 4) {
                char mac[256];
                GetWindowTextA(hWolMac, mac, 256);
                if (SendWOL(std::string(mac)))
                    MessageBoxA(hwnd, "WOL packet sent!", "Success", MB_OK);
                else
                    MessageBoxA(hwnd, "Invalid MAC address", "Error", MB_OK);
            }
            else if (LOWORD(wp) == 5) {
                g_logged_in = false;
                g_token = "";
                DestroyWindow(hwnd);
                CreateWindowA("NexusLoginWindow", "Nexus Remote", WS_OVERLAPPEDWINDOW,
                    CW_USEDEFAULT, CW_USEDEFAULT, 420, 450, NULL, NULL, GetModuleHandle(NULL), NULL);
            }
            break;
        
        case WM_PAINT: {
            PAINTSTRUCT ps;
            HDC hdc = BeginPaint(hwnd, &ps);
            if (g_logged_in) DrawMainScreen(hdc, rc);
            else DrawLoginScreen(hdc, rc);
            EndPaint(hwnd, &ps);
            break;
        }
        
        case WM_CTLCOLORSTATIC: {
            HDC hdc = (HDC)wp;
            SetBkColor(hdc, RGB(10, 10, 26));
            SetTextColor(hdc, RGB(224, 224, 224));
            return (LRESULT)CreateSolidBrush(RGB(10, 10, 26));
        }
        
        case WM_CTLCOLOREDIT: {
            HDC hdc = (HDC)wp;
            SetBkColor(hdc, RGB(15, 15, 26));
            SetTextColor(hdc, RGB(224, 224, 224));
            return (LRESULT)CreateSolidBrush(RGB(15, 15, 26));
        }
        
        case WM_DESTROY:
            PostQuitMessage(0);
            break;
        
        default:
            return DefWindowProcA(hwnd, msg, wp, lp);
    }
    return 0;
}

// ==================== MAIN ====================
int WINAPI WinMain(HINSTANCE hI, HINSTANCE, LPSTR, int nCS) {
    // Init GDI+
    GdiplusStartupInput gdi;
    ULONG_PTR gdiToken;
    GdiplusStartup(&gdiToken, &gdi, NULL);
    
    // Init Winsock for WOL
    WSADATA wsa;
    WSAStartup(MAKEWORD(2,2), &wsa);
    
    // Window class
    WNDCLASSA wc = {};
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hI;
    wc.lpszClassName = "NexusLoginWindow";
    wc.hbrBackground = CreateSolidBrush(RGB(10, 10, 26));
    wc.hCursor = LoadCursorA(NULL, IDC_ARROW);
    RegisterClassA(&wc);
    
    HWND hwnd = CreateWindowA("NexusLoginWindow", "Nexus Remote v4.0",
        WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 500, 550,
        NULL, NULL, hI, NULL);
    
    if (!hwnd) return 0;
    
    ShowWindow(hwnd, nCS);
    UpdateWindow(hwnd);
    
    MSG msg;
    while (GetMessageA(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageA(&msg);
    }
    
    WSACleanup();
    GdiplusShutdown(gdiToken);
    return 0;
}
