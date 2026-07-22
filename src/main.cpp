#include "../include/gamepad_manager.h"
#include "../include/socket_utils.h"
#include <windows.h>
#include <gdiplus.h>
#include <iostream>
#include <thread>
#include <atomic>
#include <string>
#include <vector>
#include <algorithm>
#include <winhttp.h>
#include <fstream>
#include <cstdio>

#pragma comment(lib, "gdiplus.lib")
#pragma comment(lib, "winhttp.lib")
using namespace Gdiplus;

// ==================== Nexus Server Integration ====================
static std::string g_serverUrl = "nexus-remote.onrender.com";
static std::string g_peerId = "";
static bool g_registered = false;
static std::string g_peers_list = "";

static size_t write_callback(char* ptr, size_t size, size_t nmemb, std::string* data) {
    data->append(ptr, size * nmemb);
    return size * nmemb;
}

static bool http_request(const std::string& method, const std::string& path, const std::string& json, std::string& response) {
    HINTERNET hSession = WinHttpOpen(L"Nexus Remote/2.0", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, NULL, NULL, 0);
    if (!hSession) return false;
    
    std::wstring whost(g_serverUrl.begin(), g_serverUrl.end());
    HINTERNET hConnect = WinHttpConnect(hSession, whost.c_str(), 443, 0);
    if (!hConnect) { WinHttpCloseHandle(hSession); return false; }
    
    std::wstring wpath(path.begin(), path.end());
    LPCWSTR m = (method == "POST") ? L"POST" : L"GET";
    HINTERNET hRequest = WinHttpOpenRequest(hConnect, m, wpath.c_str(), NULL, NULL, NULL, WINHTTP_FLAG_SECURE);
    if (!hRequest) { WinHttpCloseHandle(hConnect); WinHttpCloseHandle(hSession); return false; }
    
    if (method == "POST" && !json.empty()) {
        std::wstring headers = L"Content-Type: application/json\r\n";
        WinHttpAddRequestHeaders(hRequest, headers.c_str(), -1, WINHTTP_ADDREQ_FLAG_ADD);
        WinHttpSendRequest(hRequest, headers.c_str(), -1, (LPVOID)json.c_str(), json.size(), json.size(), 0);
    } else {
        WinHttpSendRequest(hRequest, NULL, 0, NULL, 0, 0, 0);
    }
    
    WinHttpReceiveResponse(hRequest, NULL);
    
    char buffer[4096];
    DWORD bytesRead;
    while (WinHttpReadData(hRequest, buffer, sizeof(buffer), &bytesRead) && bytesRead > 0) {
        response.append(buffer, bytesRead);
    }
    
    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);
    return true;
}

static void register_device() {
    if (g_registered) return;
    
    char hostname[256];
    DWORD size = 256;
    GetComputerNameA(hostname, &size);
    
    g_peerId = std::string(hostname) + "-" + std::to_string(GetTickCount64());
    
    std::string json = "{\"peer_id\":\"" + g_peerId + "\",\"platform\":\"windows\",\"compression\":\"zstd\",\"encryption\":\"aes_gcm\"}";
    std::string response;
    
    if (http_request("POST", "/register", json, response)) {
        g_registered = true;
        std::cout << "[Nexus] Registered as: " << g_peerId << std::endl;
    }
}

static void refresh_peers() {
    std::string response;
    if (http_request("GET", "/peers", "", response)) {
        g_peers_list = response;
    }
}
// ==================== End Nexus Integration ====================

static std::atomic<bool> running{true}, capturing{false};
static bool gamepadEnabled = true, darkTheme = true, autoHideGamepad = true;
static int activeTab = 0, g_port = 8080, fps = 30, bitrate = 5;
static HWND hMainWnd = nullptr;
static RECT clientRect;

// Colors
static Color bg(12,12,24), card(22,22,42), accent(99,102,241), accentHover(129,140,248);
static Color text(224,224,224), gray(140,140,160), green(52,211,153), red(248,113,113), white(255,255,255);

static std::string statusText = "Ready", deviceId = "NEXUS-" + std::to_string(rand()%9000+1000), devicePassword = "nexus123";

struct Tab { RECT r; std::wstring name; };
static std::vector<Tab> tabs;
static RECT startBtn, gamepadToggle, connectBtn, refreshBtn;

LRESULT CALLBACK WndProc(HWND,UINT,WPARAM,LPARAM);
void StartCapture(), StopCapture(), StartHttpServer();
void RegisterWithServer();

void DrawModernUI(HWND hwnd) {
    PAINTSTRUCT ps; HDC hdc = BeginPaint(hwnd, &ps);
    GetClientRect(hwnd, &clientRect);
    int w = clientRect.right, h = clientRect.bottom;
    float scale = min(w/720.0f, h/520.0f);
    if (scale < 1.0f) scale = 1.0f;
    
    HDC memDC = CreateCompatibleDC(hdc);
    HBITMAP bmp = CreateCompatibleBitmap(hdc, w, h);
    SelectObject(memDC, bmp);
    Graphics g(memDC);
    g.SetSmoothingMode(SmoothingModeAntiAlias);
    g.SetTextRenderingHint(TextRenderingHintAntiAlias);
    
    // Background
    SolidBrush bgBr(bg); g.FillRectangle(&bgBr, 0, 0, w, h);
    
    // Title
    Font titleFont(L"Segoe UI", 24*scale, FontStyleBold);
    SolidBrush accentBr(accent);
    g.DrawString(L"Nexus Remote", -1, &titleFont, PointF(25*scale, 15*scale), &accentBr);
    
    // Tabs
    tabs.clear();
    const wchar_t* names[] = {L"Devices", L"Settings", L"Gamepad", L"Files", L"Account", L"Security", L"Logs"};
    int tabCount = 7, tabY = (int)(65*scale);
    float tabW = min((w-50*scale)/tabCount, 130.0f*scale);
    
    for (int i = 0; i < tabCount; i++) {
        int tx = (int)(25*scale + i*tabW);
        RECT tr = {tx, tabY, (int)(tx+tabW-4*scale), (int)(tabY+34*scale)};
        tabs.push_back({tr, names[i]});
        
        SolidBrush tabBr(i==activeTab ? accent : card);
        g.FillRectangle(&tabBr, tr.left, tr.top, tr.right-tr.left, tr.bottom-tr.top);
        
        Font tabFont(L"Segoe UI", 10*scale, i==activeTab ? FontStyleBold : FontStyleRegular);
        SolidBrush tabTextBr(i==activeTab ? white : gray);
        RectF trf((float)tr.left, (float)tr.top, (float)(tr.right-tr.left), (float)(tr.bottom-tr.top));
        StringFormat sf; sf.SetAlignment(StringAlignmentCenter); sf.SetLineAlignment(StringAlignmentCenter);
        g.DrawString(names[i], -1, &tabFont, trf, &sf, &tabTextBr);
    }
    
    // Card
    int cardY = (int)(110*scale), cardH = h - cardY - (int)(45*scale);
    SolidBrush cardBr(card);
    g.FillRectangle(&cardBr, (int)(25*scale), cardY, (int)(w-50*scale), cardH);
    
    Font h2(L"Segoe UI", 14*scale, FontStyleBold), info(L"Segoe UI", 10*scale);
    SolidBrush whiteBr(white), grayBr(gray);
    int cx = (int)(45*scale), cy = cardY + (int)(20*scale);
    
    startBtn = {0}; gamepadToggle = {0}; connectBtn = {0}; refreshBtn = {0};
    
    switch (activeTab) {
        case 0: { // Devices
            g.DrawString(L"My Devices", -1, &h2, PointF((float)cx, (float)cy), &whiteBr);
            
            // Device ID
            std::wstring did(deviceId.begin(), deviceId.end());
            g.DrawString((L"Device ID: " + did).c_str(), -1, &info, PointF((float)cx, (float)(cy+30*scale)), &grayBr);
            
            // Nexus Server Status
            std::wstring nexusStatus = g_registered ? L"Nexus Server: CONNECTED" : L"Nexus Server: Connecting...";
            SolidBrush statusBr(g_registered ? green : gray);
            g.DrawString(nexusStatus.c_str(), -1, &info, PointF((float)cx, (float)(cy+52*scale)), &statusBr);
            
            // Peer ID на сервере
            if (g_registered) {
                std::wstring pid(g_peerId.begin(), g_peerId.end());
                g.DrawString((L"Peer: " + pid).c_str(), -1, &info, PointF((float)cx, (float)(cy+74*scale)), &SolidBrush(green));
            }
            
            // Refresh button
            int rx = (int)(w - 160*scale);
            refreshBtn = {rx, cy, rx + (int)(120*scale), cy + (int)(28*scale)};
            SolidBrush refBr(accent);
            g.FillRectangle(&refBr, rx, cy, (int)(120*scale), (int)(28*scale));
            Font btnFont(L"Segoe UI", 9*scale, FontStyleBold);
            RectF refRf((float)rx, (float)cy, (float)(120*scale), (float)(28*scale));
            StringFormat refSf; refSf.SetAlignment(StringAlignmentCenter); refSf.SetLineAlignment(StringAlignmentCenter);
            g.DrawString(L"Refresh", -1, &btnFont, refRf, &refSf, &whiteBr);
            
            g.DrawString(L"Connect to Device", -1, &h2, PointF((float)cx, (float)(cy+105*scale)), &whiteBr);
            
            // Connect to peer button
            int cbx = cx, cby = (int)(cy+135*scale);
            connectBtn = {cbx, cby, cbx + (int)(160*scale), cby + (int)(36*scale)};
            SolidBrush connBr(green);
            g.FillRectangle(&connBr, cbx, cby, (int)(160*scale), (int)(36*scale));
            Font bf(L"Segoe UI", 11*scale, FontStyleBold);
            RectF cbrf((float)cbx, (float)cby, (float)(160*scale), (float)(36*scale));
            StringFormat bsf; bsf.SetAlignment(StringAlignmentCenter); bsf.SetLineAlignment(StringAlignmentCenter);
            SolidBrush wbr(white);
            g.DrawString(L"Connect Peer", -1, &bf, cbrf, &bsf, &wbr);
            break;
        }
        case 1: // Settings
            g.DrawString(L"Capture Settings", -1, &h2, PointF((float)cx, (float)cy), &whiteBr);
            g.DrawString((L"Codec: Auto (H.264)   |   FPS: " + std::to_wstring(fps) + L"   |   Bitrate: " + std::to_wstring(bitrate) + L" Mbps").c_str(), -1, &info, PointF((float)cx, (float)(cy+35*scale)), &grayBr);
            g.DrawString(L"Resolution: Auto (detect)", -1, &info, PointF((float)cx, (float)(cy+60*scale)), &grayBr);
            g.DrawString(L"Server: nexus-remote.onrender.com", -1, &info, PointF((float)cx, (float)(cy+85*scale)), &SolidBrush(green));
            break;
        case 2: // Gamepad
            g.DrawString(L"Gamepad Settings", -1, &h2, PointF((float)cx, (float)cy), &whiteBr);
            g.DrawString((L"Virtual Gamepad: " + std::wstring(gamepadEnabled ? L"ON" : L"OFF")).c_str(), -1, &info, PointF((float)cx, (float)(cy+35*scale)), gamepadEnabled ? &SolidBrush(green) : &grayBr);
            g.DrawString((L"Auto-hide with physical controller: " + std::wstring(autoHideGamepad ? L"ON" : L"OFF")).c_str(), -1, &info, PointF((float)cx, (float)(cy+60*scale)), &grayBr);
            
            gamepadToggle = {(int)(cx), (int)(cy+35*scale), (int)(cx+280*scale), (int)(cy+55*scale)};
            break;
        case 3: // Files
            g.DrawString(L"Cloud Storage", -1, &h2, PointF((float)cx, (float)cy), &whiteBr);
            g.DrawString(L"Google Drive, Yandex Disk, OneDrive, Dropbox", -1, &info, PointF((float)cx, (float)(cy+35*scale)), &grayBr);
            break;
        case 4: // Account
            g.DrawString(L"Account", -1, &h2, PointF((float)cx, (float)cy), &whiteBr);
            g.DrawString(L"Sign in with Google or GitHub", -1, &info, PointF((float)cx, (float)(cy+35*scale)), &grayBr);
            break;
        case 5: // Security
            g.DrawString(L"Security", -1, &h2, PointF((float)cx, (float)cy), &whiteBr);
            g.DrawString(L"Encryption: AES-256-GCM   |   Compression: ZSTD", -1, &info, PointF((float)cx, (float)(cy+35*scale)), &grayBr);
            break;
        case 6: // Logs
            g.DrawString(L"Connection Logs", -1, &h2, PointF((float)cx, (float)cy), &whiteBr);
            g.DrawString(L"Server: nexus-remote.onrender.com:10000", -1, &info, PointF((float)cx, (float)(cy+35*scale)), &grayBr);
            break;
    }
    
    // Bottom bar
    int barY = h - (int)(38*scale);
    SolidBrush barBr(Color(18,18,38));
    g.FillRectangle(&barBr, 0, barY, w, (int)(38*scale));
    
    SolidBrush dotBr(g_registered ? green : red);
    g.FillEllipse(&dotBr, (int)(15*scale), barY+(int)(13*scale), (int)(12*scale), (int)(12*scale));
    
    std::wstring st(g_registered ? L"Server Connected" : L"Disconnected");
    Font barFont(L"Segoe UI", 9*scale);
    g.DrawString(st.c_str(), -1, &barFont, PointF((float)(35*scale), (float)(barY+10*scale)), &grayBr);
    
    std::wstring wp = L"nexus-remote.onrender.com";
    RectF wpr(0, (float)barY, (float)(w-20*scale), (float)(38*scale));
    StringFormat wpsf; wpsf.SetAlignment(StringAlignmentFar); wpsf.SetLineAlignment(StringAlignmentCenter);
    g.DrawString(wp.c_str(), -1, &barFont, wpr, &wpsf, &grayBr);
    
    BitBlt(hdc, 0, 0, w, h, memDC, 0, 0, SRCCOPY);
    DeleteDC(memDC); DeleteObject(bmp);
    EndPaint(hwnd, &ps);
}


// Диалог ввода Peer ID
static INT_PTR CALLBACK PeerDialogProc(HWND hDlg, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
        case WM_INITDIALOG:
            SetWindowTextA(hDlg, "Connect to Peer");
            SetDlgItemTextA(hDlg, 1001, "Enter Peer ID:");
            SetDlgItemTextA(hDlg, 1002, "");
            SetWindowTextA(GetDlgItem(hDlg, IDOK), "Connect");
            SetWindowTextA(GetDlgItem(hDlg, IDCANCEL), "Cancel");
            return TRUE;
        case WM_COMMAND:
            if (LOWORD(wParam) == IDOK) {
                char* peerId = (char*)lParam;
                GetDlgItemTextA(hDlg, 1002, peerId, 256);
                if (strlen(peerId) > 0) {
                    EndDialog(hDlg, 1);
                } else {
                    MessageBoxA(hDlg, "Please enter a Peer ID", "Error", MB_OK);
                }
                return TRUE;
            }
            if (LOWORD(wParam) == IDCANCEL) {
                EndDialog(hDlg, 0);
                return TRUE;
            }
            break;
    }
    return FALSE;
}

int WINAPI WinMain(HINSTANCE hI, HINSTANCE, LPSTR, int nCS) {
    GdiplusStartupInput gi; ULONG_PTR gt; GdiplusStartup(&gt, &gi, nullptr);
    sockets_init(); srand((unsigned)time(nullptr));
    
    WNDCLASSA wc = {}; wc.lpfnWndProc = WndProc; wc.hInstance = hI;
    wc.lpszClassName = "NexusRemoteMain"; wc.hCursor = LoadCursorA(nullptr, IDC_ARROW);
    wc.hbrBackground = CreateSolidBrush(RGB(12,12,24));
    RegisterClassA(&wc);
    
    hMainWnd = CreateWindowA("NexusRemoteMain", "Nexus Remote v2.1",
        WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 750, 540,
        nullptr, nullptr, hI, nullptr);
    
    // Register with Nexus server in background
    std::thread([]() {
        Sleep(1500);
        RegisterWithServer();
    }).detach();
    
    StartHttpServer();
    ShowWindow(hMainWnd, nCS);
    
    MSG msg;
    while (GetMessageA(&msg, nullptr, 0, 0)) { TranslateMessage(&msg); DispatchMessageA(&msg); }
    
    running = false; sockets_cleanup(); GdiplusShutdown(gt);
    return 0;
}

void RegisterWithServer() {
    register_device();
    InvalidateRect(hMainWnd, nullptr, TRUE);
}

LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
        case WM_PAINT: DrawModernUI(hwnd); break;
        case WM_SIZE: InvalidateRect(hwnd, nullptr, TRUE); break;
        case WM_GETMINMAXINFO: {
            MINMAXINFO* m = (MINMAXINFO*)lp;
            m->ptMinTrackSize = {640, 480};
            break;
        }
        case WM_LBUTTONDOWN: {
            int x = LOWORD(lp), y = HIWORD(lp);
            for (int i = 0; i < (int)tabs.size(); i++) {
                if (x >= tabs[i].r.left && x <= tabs[i].r.right && y >= tabs[i].r.top && y <= tabs[i].r.bottom) {
                    activeTab = i; InvalidateRect(hwnd, nullptr, TRUE); break;
                }
            }
            if (activeTab == 0 && connectBtn.right && x >= connectBtn.left && x <= connectBtn.right && y >= connectBtn.top && y <= connectBtn.bottom) {
                MessageBoxA(hwnd, "Connect to peer: Use the Python agent or WebUI to connect", "Nexus Remote", MB_OK);
            }
            if (activeTab == 0 && refreshBtn.right && x >= refreshBtn.left && x <= refreshBtn.right && y >= refreshBtn.top && y <= refreshBtn.bottom) {
                RegisterWithServer();
            }
            if (activeTab == 2 && gamepadToggle.right && x >= gamepadToggle.left && x <= gamepadToggle.right && y >= gamepadToggle.top && y <= gamepadToggle.bottom) {
                gamepadEnabled = !gamepadEnabled;
                InvalidateRect(hwnd, nullptr, TRUE);
            }
            break;
        }
        case WM_DESTROY: running = false; PostQuitMessage(0); break;
        default: return DefWindowProcA(hwnd, msg, wp, lp);
    }
    return 0;
}

void StartCapture() { }
void StopCapture() { }

void StartHttpServer() {
    std::thread([]() {
        socket_t ls = create_listen_socket(g_port);
        if (ls < 0) return;
        while (running) {
            socket_t c = accept_client(ls);
            if (c >= 0) {
                char b[512]; recv(c, b, sizeof(b)-1, 0);
                std::string r = "HTTP/1.1 200 OK\r\n\r\nNexus API";
                send(c, r.c_str(), (int)r.size(), 0);
                close_socket(c);
            }
        }
        close_socket(ls);
    }).detach();
}



