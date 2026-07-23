// nexus_modern_ui.cpp - FULL C++ UI with Working Login + Main Screen
#include <windows.h>
#include <winhttp.h>
#include <gdiplus.h>
#include <string>
#include <fstream>
#include <algorithm>

#pragma comment(lib, "winhttp.lib")
#pragma comment(lib, "gdiplus.lib")
#pragma comment(lib, "ws2_32.lib")

using namespace Gdiplus;
using std::min;

#ifndef EM_SETCUEBANNER
#define EM_SETCUEBANNER 0x1501
#endif

// ==================== SESSION ====================
static std::string SESSION_FILE = "nexus_session.dat";

static void SaveSession(const std::string& token, const std::string& peer, const std::string& email) {
    std::ofstream f(SESSION_FILE);
    if (f.is_open()) { f << token << "\n" << peer << "\n" << email; f.close(); }
}

static bool LoadSession(std::string& token, std::string& peer, std::string& email) {
    std::ifstream f(SESSION_FILE);
    if (f.is_open()) {
        std::getline(f, token); std::getline(f, peer); std::getline(f, email);
        f.close();
        return !token.empty() && !peer.empty() && !email.empty();
    }
    return false;
}

static void ClearSession() { DeleteFileA(SESSION_FILE.c_str()); }

// ==================== GLOBALS ====================
static std::string g_token, g_peer_id, g_email;
static std::string g_server = "nexus-remote.onrender.com";
static bool g_logged_in = false, g_streaming = false;
static HWND hMainWnd;
static HFONT hFont, hFontBold, hFontSmall;

// Login controls
static HWND hEmailLabel, hEmail, hPassLabel, hPassword, hLoginBtn, hStatus, hRegisterLink;
// Main controls
static HWND hPeerLabel, hPeerInput, hConnectBtn, hStreamBtn, hWolLabel, hWolMac, hWolBtn, hLogoutBtn;

// ==================== HTTP ====================
static std::string HttpPost(const std::string& path, const std::string& json) {
    std::wstring host(g_server.begin(), g_server.end());
    std::wstring wpath(path.begin(), path.end());
    HINTERNET hS = WinHttpOpen(L"Nexus/4.0", 0, 0, 0, 0);
    if(!hS) return "";
    HINTERNET hC = WinHttpConnect(hS, host.c_str(), 443, 0);
    if(!hC) { WinHttpCloseHandle(hS); return ""; }
    HINTERNET hR = WinHttpOpenRequest(hC, L"POST", wpath.c_str(), 0, 0, 0, WINHTTP_FLAG_SECURE);
    if(!hR) { WinHttpCloseHandle(hC); WinHttpCloseHandle(hS); return ""; }
    std::wstring hdrs = L"Content-Type: application/json\r\n";
    WinHttpAddRequestHeaders(hR, hdrs.c_str(), -1, WINHTTP_ADDREQ_FLAG_ADD);
    std::string body = json;
    WinHttpSendRequest(hR, hdrs.c_str(), -1, (LPVOID)body.c_str(), body.size(), body.size(), 0);
    WinHttpReceiveResponse(hR, 0);
    char b[4096]; DWORD r; std::string resp;
    while(WinHttpReadData(hR, b, sizeof(b), &r) && r>0) resp.append(b, r);
    WinHttpCloseHandle(hR); WinHttpCloseHandle(hC); WinHttpCloseHandle(hS);
    return resp;
}

// ==================== WOL ====================
static bool SendWOL(const std::string& mac) {
    std::string c; for(char ch:mac) if(ch!=':'&&ch!='-'&&ch!=' ') c+=ch;
    if(c.size()!=12) return false;
    unsigned char pkt[102]; memset(pkt, 0xFF, 6);
    for(int i=0;i<16;i++) for(int j=0;j<6;j++) {
        char bs[3]={c[j*2],c[j*2+1],0};
        pkt[6+i*6+j]=(unsigned char)strtol(bs,0,16);
    }
    SOCKET s=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    if(s==INVALID_SOCKET) return false;
    BOOL bc=TRUE; setsockopt(s,SOL_SOCKET,SO_BROADCAST,(char*)&bc,sizeof(bc));
    sockaddr_in a={}; a.sin_family=AF_INET; a.sin_port=htons(9);
    a.sin_addr.s_addr=inet_addr("255.255.255.255");
    sendto(s,(char*)pkt,sizeof(pkt),0,(sockaddr*)&a,sizeof(a));
    closesocket(s); return true;
}

// ==================== LOGIN LOGIC ====================
static void DestroyLoginControls() {
    DestroyWindow(hEmailLabel); DestroyWindow(hEmail);
    DestroyWindow(hPassLabel); DestroyWindow(hPassword);
    DestroyWindow(hLoginBtn); DestroyWindow(hStatus);
    DestroyWindow(hRegisterLink);
}

static void DestroyMainControls() {
    DestroyWindow(hPeerLabel); DestroyWindow(hPeerInput);
    DestroyWindow(hConnectBtn); DestroyWindow(hStreamBtn);
    DestroyWindow(hWolLabel); DestroyWindow(hWolMac);
    DestroyWindow(hWolBtn); DestroyWindow(hLogoutBtn);
}

static void DoLogin(HWND hwnd) {
    char e[256]={0}, p[256]={0};
    GetWindowTextA(hEmail, e, 256);
    GetWindowTextA(hPassword, p, 256);
    
    if(strlen(e)==0 || strlen(p)==0) {
        SetWindowTextA(hStatus, "Enter email and password");
        return;
    }
    
    SetWindowTextA(hStatus, "Logging in...");
    UpdateWindow(hwnd);
    
    std::string json = "{\"email\":\"" + std::string(e) + "\",\"password\":\"" + std::string(p) + "\"}";
    std::string resp = HttpPost("/api/auth/login", json);
    
    if(resp.find("\"token\":\"") != std::string::npos) {
        size_t t1 = resp.find("\"token\":\"") + 9;
        size_t t2 = resp.find("\"", t1);
        g_token = resp.substr(t1, t2 - t1);
        
        size_t p1 = resp.find("\"peer_id\":\"") + 12;
        size_t p2 = resp.find("\"", p1);
        g_peer_id = resp.substr(p1, p2 - p1);
        
        g_email = e;
        g_logged_in = true;
        
        SaveSession(g_token, g_peer_id, g_email);
        
        DestroyLoginControls();
        InvalidateRect(hwnd, NULL, TRUE);
        UpdateWindow(hwnd);
        MessageBoxA(hwnd, ("Welcome " + g_email + "!\nPeer: " + g_peer_id).c_str(), "Nexus Remote", MB_OK | MB_ICONINFORMATION);
    } else {
        SetWindowTextA(hStatus, "Invalid credentials");
    }
}

static void DoLogout(HWND hwnd) {
    g_logged_in = false;
    ClearSession();
    DestroyMainControls();
    InvalidateRect(hwnd, NULL, TRUE);
}

// ==================== STREAMING ====================
static void StartStream() {
    char p[256]={0};
    GetWindowTextA(hPeerInput, p, 256);
    if(strlen(p)==0) { MessageBoxA(hMainWnd, "Enter Peer ID", "Error", MB_OK); return; }
    
    std::string json = "{\"source\":\"" + g_peer_id + "\",\"target\":\"" + std::string(p) + "\",\"quality\":\"high\"}";
    std::string resp = HttpPost("/start_stream", json);
    
    if(resp.find("\"streaming\"") != std::string::npos) {
        g_streaming = true;
        SetWindowTextA(hStreamBtn, "Stop Stream");
        MessageBoxA(hMainWnd, "Stream started!", "Success", MB_OK);
    }
}

static void StopStream() {
    g_streaming = false;
    SetWindowTextA(hStreamBtn, "Start Stream");
    HttpPost("/stop_stream", "{}");
}

// ==================== PAINTING ====================
static void DrawLoginScreen(HDC hdc, RECT& rc) {
    Graphics g(hdc);
    g.SetSmoothingMode(SmoothingModeAntiAlias);
    
    // Background
    SolidBrush bgBr(Color(10,10,26));
    g.FillRectangle(&bgBr, 0, 0, rc.right, rc.bottom);
    
    // Title
    Font titleFont(L"Segoe UI", 32, FontStyleBold);
    SolidBrush accentBr(Color(99,102,241));
    StringFormat sf; sf.SetAlignment(StringAlignmentCenter);
    RectF titleRect(0, 40, (REAL)rc.right, 50);
    g.DrawString(L"Nexus Remote", -1, &titleFont, titleRect, &sf, &accentBr);
    
    // Subtitle
    Font subFont(L"Segoe UI", 13);
    SolidBrush grayBr(Color(136,136,160));
    RectF subRect(0, 85, (REAL)rc.right, 25);
    g.DrawString(L"Secure Remote Desktop & Streaming", -1, &subFont, subRect, &sf, &grayBr);
    
    // Features
    Font featFont(L"Segoe UI", 11);
    SolidBrush greenBr(Color(34,197,94));
    RectF featRect(0, 115, (REAL)rc.right, 20);
    g.DrawString(L"E2E Encrypted  |  4K Streaming  |  Multi-Platform", -1, &featFont, featRect, &sf, &greenBr);
}

static void DrawMainScreen(HDC hdc, RECT& rc) {
    Graphics g(hdc);
    g.SetSmoothingMode(SmoothingModeAntiAlias);
    
    // Background
    SolidBrush bgBr(Color(10,10,26));
    g.FillRectangle(&bgBr, 0, 0, rc.right, rc.bottom);
    
    // Top bar
    SolidBrush topBr(Color(13,13,36));
    g.FillRectangle(&topBr, 0, 0, rc.right, 45);
    
    Font titleF(L"Segoe UI", 16, FontStyleBold);
    SolidBrush accentBr(Color(99,102,241));
    g.DrawString(L"Nexus Remote", -1, &titleF, PointF(15, 10), &accentBr);
    
    Font userF(L"Segoe UI", 10);
    SolidBrush greenBr(Color(34,197,94));
    std::wstring wemail(g_email.begin(), g_email.end());
    g.DrawString((L"User: " + wemail).c_str(), -1, &userF, PointF(200, 15), &greenBr);
    
    // Cards
    int cardX = 15, cardW = rc.right - 30;
    int y = 60;
    
    // Card 1: Connect
    SolidBrush cardBr(Color(21,21,48));
    g.FillRectangle(&cardBr, cardX, y, cardW, 130);
    
    Font h2(L"Segoe UI", 15, FontStyleBold);
    g.DrawString(L"Connect to Device", -1, &h2, PointF(30, y+15), &accentBr);
    
    Font info(L"Segoe UI", 10);
    SolidBrush grayBr(Color(136,136,160));
    std::wstring wpeer(g_peer_id.begin(), g_peer_id.end());
    g.DrawString((L"Your Peer ID: " + wpeer).c_str(), -1, &info, PointF(30, y+45), &grayBr);
    
    // Card 2: Streaming
    y += 148;
    g.FillRectangle(&cardBr, cardX, y, cardW, 100);
    g.DrawString(L"Streaming", -1, &h2, PointF(30, y+15), &accentBr);
    
    std::string ss = g_streaming ? "Active" : "Inactive";
    Color sc = g_streaming ? Color(34,197,94) : Color(136,136,160);
    SolidBrush sb(sc);
    std::wstring ws(ss.begin(), ss.end());
    g.DrawString((L"Status: " + ws).c_str(), -1, &info, PointF(30, y+45), &sb);
    
    // Card 3: WOL
    y += 118;
    g.FillRectangle(&cardBr, cardX, y, cardW, 80);
    g.DrawString(L"Wake-on-LAN", -1, &h2, PointF(30, y+15), &accentBr);
    g.DrawString(L"Wake devices remotely", -1, &info, PointF(30, y+42), &grayBr);
}

// ==================== WINDOW PROC ====================
LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch(msg) {
        case WM_CREATE: {
            hMainWnd = hwnd;
            
            // Load session
            std::string tok, peer, em;
            if(LoadSession(tok, peer, em)) {
                g_token = tok; g_peer_id = peer; g_email = em;
                g_logged_in = true;
            }
            break;
        }
        
        case WM_PAINT: {
            PAINTSTRUCT ps;
            HDC hdc = BeginPaint(hwnd, &ps);
            RECT rc; GetClientRect(hwnd, &rc);
            
            if(!g_logged_in) {
                DrawLoginScreen(hdc, rc);
            } else {
                DrawMainScreen(hdc, rc);
            }
            
            EndPaint(hwnd, &ps);
            break;
        }
        
        case WM_CTLCOLORSTATIC: {
            HDC hdc = (HDC)wp;
            SetBkColor(hdc, RGB(10,10,26));
            SetTextColor(hdc, RGB(224,224,224));
            return (LRESULT)CreateSolidBrush(RGB(10,10,26));
        }
        
        case WM_CTLCOLOREDIT: {
            HDC hdc = (HDC)wp;
            SetBkColor(hdc, RGB(15,15,26));
            SetTextColor(hdc, RGB(224,224,224));
            return (LRESULT)CreateSolidBrush(RGB(15,15,26));
        }
        
        case WM_COMMAND: {
            int id = LOWORD(wp);
            
            if(!g_logged_in && id == 1) {
                DoLogin(hwnd);
                if(g_logged_in) {
                    // Create main controls
                    RECT rc; GetClientRect(hwnd, &rc);
                    int cardW = rc.right - 30;
                    int y = 140;
                    
                    hPeerLabel = CreateWindowA("STATIC", "Peer ID:", WS_VISIBLE|WS_CHILD, 15, y, 100, 20, hwnd, 0,0,0);
                    hPeerInput = CreateWindowA("EDIT", "", WS_VISIBLE|WS_CHILD|WS_BORDER|ES_CENTER, 15, y+22, (int)(cardW*0.6), 30, hwnd, 0,0,0);
                    SendMessageA(hPeerInput, EM_SETCUEBANNER, TRUE, (LPARAM)"Enter Peer ID...");
                    hConnectBtn = CreateWindowA("BUTTON", "Connect", WS_VISIBLE|WS_CHILD|BS_PUSHBUTTON, 15+(int)(cardW*0.6)+8, y+22, (int)(cardW*0.38), 30, hwnd, (HMENU)2,0,0);
                    
                    y += 75;
                    hStreamBtn = CreateWindowA("BUTTON", "Start Stream", WS_VISIBLE|WS_CHILD|BS_PUSHBUTTON, 15, y, cardW, 40, hwnd, (HMENU)3,0,0);
                    
                    y += 58;
                    hWolLabel = CreateWindowA("STATIC", "MAC Address:", WS_VISIBLE|WS_CHILD, 15, y, 100, 20, hwnd, 0,0,0);
                    hWolMac = CreateWindowA("EDIT", "AA:BB:CC:DD:EE:FF", WS_VISIBLE|WS_CHILD|WS_BORDER|ES_CENTER, 15, y+22, (int)(cardW*0.6), 30, hwnd, 0,0,0);
                    hWolBtn = CreateWindowA("BUTTON", "Wake Up", WS_VISIBLE|WS_CHILD|BS_PUSHBUTTON, 15+(int)(cardW*0.6)+8, y+22, (int)(cardW*0.38), 30, hwnd, (HMENU)4,0,0);
                    
                    hLogoutBtn = CreateWindowA("BUTTON", "Logout", WS_VISIBLE|WS_CHILD|BS_PUSHBUTTON, rc.right-115, 8, 100, 28, hwnd, (HMENU)5,0,0);
                    
                    InvalidateRect(hwnd, NULL, TRUE);
                }
            }
            else if(g_logged_in && id == 2) StartStream();
            else if(g_logged_in && id == 3) { if(g_streaming) StopStream(); else StartStream(); }
            else if(g_logged_in && id == 4) {
                char m[256]={0}; GetWindowTextA(hWolMac, m, 256);
                MessageBoxA(hwnd, SendWOL(std::string(m)) ? "WOL sent!" : "Invalid MAC", "WOL", MB_OK);
            }
            else if(g_logged_in && id == 5) DoLogout(hwnd);
            break;
        }
        
        case WM_DESTROY:
            PostQuitMessage(0);
            break;
        
        default:
            return DefWindowProcA(hwnd, msg, wp, lp);
    }
    return 0;
}

// ==================== CREATE LOGIN CONTROLS ====================
static void CreateLoginControls(HWND hwnd) {
    RECT rc; GetClientRect(hwnd, &rc);
    int cx = rc.right/2 - 150;
    int cy = 170;
    int cw = 300;
    
    hEmailLabel = CreateWindowA("STATIC", "Email Address", WS_VISIBLE|WS_CHILD, cx, cy, cw, 18, hwnd, 0,0,0);
    hEmail = CreateWindowA("EDIT", "", WS_VISIBLE|WS_CHILD|WS_BORDER|ES_CENTER, cx, cy+20, cw, 32, hwnd, 0,0,0);
    SendMessageA(hEmail, EM_SETCUEBANNER, TRUE, (LPARAM)"demo@nexus.com");
    
    cy += 65;
    hPassLabel = CreateWindowA("STATIC", "Password", WS_VISIBLE|WS_CHILD, cx, cy, cw, 18, hwnd, 0,0,0);
    hPassword = CreateWindowA("EDIT", "", WS_VISIBLE|WS_CHILD|WS_BORDER|ES_CENTER|ES_PASSWORD, cx, cy+20, cw, 32, hwnd, 0,0,0);
    SendMessageA(hPassword, EM_SETCUEBANNER, TRUE, (LPARAM)"demo123456");
    
    cy += 65;
    hLoginBtn = CreateWindowA("BUTTON", "Sign In", WS_VISIBLE|WS_CHILD|BS_PUSHBUTTON, cx, cy, cw, 38, hwnd, (HMENU)1,0,0);
    
    cy += 48;
    hStatus = CreateWindowA("STATIC", "", WS_VISIBLE|WS_CHILD|SS_CENTER, cx, cy, cw, 22, hwnd, 0,0,0);
    
    cy += 30;
    hRegisterLink = CreateWindowA("STATIC", "Register: nexus-remote.onrender.com", WS_VISIBLE|WS_CHILD|SS_CENTER, cx, cy, cw, 18, hwnd, 0,0,0);
}

// ==================== WINMAIN ====================
int WINAPI WinMain(HINSTANCE hI, HINSTANCE, LPSTR, int nCS) {
    GdiplusStartupInput gdi; ULONG_PTR gdT;
    GdiplusStartup(&gdT, &gdi, NULL);
    
    WSADATA wsa; WSAStartup(MAKEWORD(2,2), &wsa);
    
    WNDCLASSA wc = {};
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hI;
    wc.lpszClassName = "NexusWindow";
    wc.hbrBackground = CreateSolidBrush(RGB(10,10,26));
    wc.hCursor = LoadCursorA(NULL, IDC_ARROW);
    RegisterClassA(&wc);
    
    HWND hwnd = CreateWindowA("NexusWindow", "Nexus Remote v4.0",
        WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 500, 600,
        NULL, NULL, hI, NULL);
    
    if(!hwnd) return 0;
    
    // Create login controls initially
    CreateLoginControls(hwnd);
    
    // If session exists, auto-login
    std::string tok, peer, em;
    if(LoadSession(tok, peer, em)) {
        g_token = tok; g_peer_id = peer; g_email = em;
        g_logged_in = true;
        // Destroy login controls - they'll be recreated in WM_COMMAND
        DestroyWindow(hEmailLabel); DestroyWindow(hEmail);
        DestroyWindow(hPassLabel); DestroyWindow(hPassword);
        DestroyWindow(hLoginBtn); DestroyWindow(hStatus);
        DestroyWindow(hRegisterLink);
        // Trigger main screen creation
        PostMessageA(hwnd, WM_COMMAND, MAKEWPARAM(0,0), 0);
        InvalidateRect(hwnd, NULL, TRUE);
    }
    
    ShowWindow(hwnd, nCS);
    UpdateWindow(hwnd);
    
    MSG msg;
    while(GetMessageA(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageA(&msg);
    }
    
    WSACleanup();
    GdiplusShutdown(gdT);
    return 0;
}
