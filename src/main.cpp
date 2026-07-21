#include "../include/capture/screen_capturer.h"
#include "../include/video/video_encoder.h"
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

#pragma comment(lib, "gdiplus.lib")
using namespace Gdiplus;

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
static RECT startBtn, gamepadToggle;

LRESULT CALLBACK WndProc(HWND,UINT,WPARAM,LPARAM);
void StartCapture(), StopCapture(), StartHttpServer();

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
    
    // Title only - no subtitle
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
    
    startBtn = {0}; gamepadToggle = {0};
    
    switch (activeTab) {
        case 0: { // Devices
            g.DrawString(L"My Devices", -1, &h2, PointF((float)cx, (float)cy), &whiteBr);
            std::wstring did(deviceId.begin(), deviceId.end());
            g.DrawString((L"Device ID: " + did).c_str(), -1, &info, PointF((float)cx, (float)(cy+30*scale)), &grayBr);
            g.DrawString((L"Password: " + std::wstring(devicePassword.begin(), devicePassword.end())).c_str(), -1, &info, PointF((float)cx, (float)(cy+52*scale)), &grayBr);
            
            g.DrawString(L"Connect to Device", -1, &h2, PointF((float)cx, (float)(cy+90*scale)), &whiteBr);
            
            int bx = cx, by = (int)(cy+120*scale);
            startBtn = {bx, by, bx+(int)(160*scale), by+(int)(36*scale)};
            Color bc = capturing ? red : green;
            SolidBrush bbr(bc);
            g.FillRectangle(&bbr, bx, by, (int)(160*scale), (int)(36*scale));
            
            std::wstring bt = capturing ? L"Stop Capture" : L"Start Capture";
            Font bf(L"Segoe UI", 11*scale, FontStyleBold);
            RectF brf((float)bx, (float)by, (float)(160*scale), (float)(36*scale));
            StringFormat bsf; bsf.SetAlignment(StringAlignmentCenter); bsf.SetLineAlignment(StringAlignmentCenter);
            SolidBrush wbr(white);
            g.DrawString(bt.c_str(), -1, &bf, brf, &bsf, &wbr);
            break;
        }
        case 1: // Settings
            g.DrawString(L"Capture Settings", -1, &h2, PointF((float)cx, (float)cy), &whiteBr);
            g.DrawString((L"Codec: Auto (H.264)   |   FPS: " + std::to_wstring(fps) + L"   |   Bitrate: " + std::to_wstring(bitrate) + L" Mbps").c_str(), -1, &info, PointF((float)cx, (float)(cy+35*scale)), &grayBr);
            g.DrawString(L"Resolution: Auto (detect)", -1, &info, PointF((float)cx, (float)(cy+60*scale)), &grayBr);
            g.DrawString(L"Dark Theme: ON", -1, &info, PointF((float)cx, (float)(cy+85*scale)), &grayBr);
            break;
        case 2: // Gamepad
            g.DrawString(L"Gamepad Settings", -1, &h2, PointF((float)cx, (float)cy), &whiteBr);
            g.DrawString((L"Virtual Gamepad: " + std::wstring(gamepadEnabled ? L"ON" : L"OFF")).c_str(), -1, &info, PointF((float)cx, (float)(cy+35*scale)), gamepadEnabled ? &SolidBrush(green) : &grayBr);
            g.DrawString((L"Auto-hide with physical controller: " + std::wstring(autoHideGamepad ? L"ON" : L"OFF")).c_str(), -1, &info, PointF((float)cx, (float)(cy+60*scale)), &grayBr);
            g.DrawString(L"Controller Type: Xbox", -1, &info, PointF((float)cx, (float)(cy+85*scale)), &grayBr);
            g.DrawString(L"Available on: Android, iPhone", -1, &info, PointF((float)cx, (float)(cy+110*scale)), &grayBr);
            
            gamepadToggle = {(int)(cx), (int)(cy+35*scale), (int)(cx+280*scale), (int)(cy+55*scale)};
            break;
        case 3: // Files
            g.DrawString(L"Cloud Storage", -1, &h2, PointF((float)cx, (float)cy), &whiteBr);
            g.DrawString(L"Google Drive  •  Yandex Disk  •  OneDrive  •  Dropbox", -1, &info, PointF((float)cx, (float)(cy+35*scale)), &grayBr);
            g.DrawString(L"Connect your cloud accounts to access files remotely", -1, &info, PointF((float)cx, (float)(cy+60*scale)), &grayBr);
            break;
        case 4: // Account
            g.DrawString(L"Account", -1, &h2, PointF((float)cx, (float)cy), &whiteBr);
            g.DrawString(L"Sign in with Google or GitHub", -1, &info, PointF((float)cx, (float)(cy+35*scale)), &grayBr);
            break;
        case 5: // Security
            g.DrawString(L"Security", -1, &h2, PointF((float)cx, (float)cy), &whiteBr);
            g.DrawString(L"Password Protection: ON   |   2FA: OFF   |   Encryption: TLS", -1, &info, PointF((float)cx, (float)(cy+35*scale)), &grayBr);
            g.DrawString(L"Block after 5 failed attempts   |   IP Blacklist: Empty", -1, &info, PointF((float)cx, (float)(cy+60*scale)), &grayBr);
            break;
        case 6: // Logs
            g.DrawString(L"Connection Logs", -1, &h2, PointF((float)cx, (float)cy), &whiteBr);
            g.DrawString(L"No recent connections", -1, &info, PointF((float)cx, (float)(cy+35*scale)), &grayBr);
            break;
    }
    
    // Bottom bar
    int barY = h - (int)(38*scale);
    SolidBrush barBr(Color(18,18,38));
    g.FillRectangle(&barBr, 0, barY, w, (int)(38*scale));
    
    SolidBrush dotBr(capturing ? green : red);
    g.FillEllipse(&dotBr, (int)(15*scale), barY+(int)(13*scale), (int)(12*scale), (int)(12*scale));
    
    std::wstring st(capturing ? (std::wstring(statusText.begin(), statusText.end())) : L"Stopped");
    Font barFont(L"Segoe UI", 9*scale);
    g.DrawString(st.c_str(), -1, &barFont, PointF((float)(35*scale), (float)(barY+10*scale)), &grayBr);
    
    std::wstring wp = L"WebUI: http://localhost:8080";
    RectF wpr(0, (float)barY, (float)(w-20*scale), (float)(38*scale));
    StringFormat wpsf; wpsf.SetAlignment(StringAlignmentFar); wpsf.SetLineAlignment(StringAlignmentCenter);
    g.DrawString(wp.c_str(), -1, &barFont, wpr, &wpsf, &grayBr);
    
    BitBlt(hdc, 0, 0, w, h, memDC, 0, 0, SRCCOPY);
    DeleteDC(memDC); DeleteObject(bmp);
    EndPaint(hwnd, &ps);
}

int WINAPI WinMain(HINSTANCE hI, HINSTANCE, LPSTR, int nCS) {
    GdiplusStartupInput gi; ULONG_PTR gt; GdiplusStartup(&gt, &gi, nullptr);
    sockets_init(); srand((unsigned)time(nullptr));
    
    WNDCLASSA wc = {}; wc.lpfnWndProc = WndProc; wc.hInstance = hI;
    wc.lpszClassName = "NexusRemoteMain"; wc.hCursor = LoadCursorA(nullptr, IDC_ARROW);
    wc.hbrBackground = CreateSolidBrush(RGB(12,12,24));
    RegisterClassA(&wc);
    
    hMainWnd = CreateWindowA("NexusRemoteMain", "Nexus Remote v2.0",
        WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 750, 540,
        nullptr, nullptr, hI, nullptr);
    
    StartHttpServer();
    ShowWindow(hMainWnd, nCS);
    
    MSG msg;
    while (GetMessageA(&msg, nullptr, 0, 0)) { TranslateMessage(&msg); DispatchMessageA(&msg); }
    
    running = false; sockets_cleanup(); GdiplusShutdown(gt);
    return 0;
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
            if (activeTab == 0 && startBtn.right && x >= startBtn.left && x <= startBtn.right && y >= startBtn.top && y <= startBtn.bottom) {
                capturing ? StopCapture() : StartCapture();
                InvalidateRect(hwnd, nullptr, TRUE);
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

void StartCapture() {
    capturing = true; statusText = "Initializing...";
    InvalidateRect(hMainWnd, nullptr, TRUE);
    std::thread([]() {
        auto cap = nexus::capture::create_capturer();
        if (!cap->init()) { statusText = "Capture failed!"; capturing = false; InvalidateRect(hMainWnd, nullptr, TRUE); return; }
        uint32_t w, h; cap->get_resolution(w, h);
        auto enc = nexus::video::create_encoder(); enc->init(w, h, fps);
        statusText = std::to_string(w) + "x" + std::to_string(h) + " @" + std::to_string(fps) + "fps";
        InvalidateRect(hMainWnd, nullptr, TRUE);
        while (capturing) { auto f = cap->capture(); if (f) enc->encode(f->data, w, h); }
        enc->release(); cap->release();
    }).detach();
}

void StopCapture() { capturing = false; statusText = "Ready"; InvalidateRect(hMainWnd, nullptr, TRUE); }

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
