#include <windows.h>
#include <gdiplus.h>
#include <string>
#include <vector>
#pragma comment(lib, "gdiplus.lib")
using namespace Gdiplus;
using std::min;

// ==================== GLOBALS ====================
int g_tab = 0;
std::wstring g_user = L"demo@nexus.com";
std::wstring g_peer = L"nexus-129025594271";
bool g_streaming = false;

// Colors
Color bg(10,10,26), card(21,21,48), accent(99,102,241);
Color green(34,197,94), red(239,68,68), orange(245,158,11);
Color txt(224,224,224), gray(136,136,160), white(255,255,255);
Color darkBtn(30,30,50), btnBorder(60,60,100);

// ==================== DRAWING HELPERS ====================
void DrawButton(Graphics& g, int x, int y, int w, int h, const wchar_t* text, Color color, bool filled=true) {
    // Button background
    SolidBrush bgBr(filled ? color : Color(0,0,0,0));
    g.FillRectangle(&bgBr, x, y, w, h);
    
    // Border
    Pen borderPen(filled ? Color(color.GetA(), min(color.GetR()+40,255), min(color.GetG()+40,255), min(color.GetB()+40,255)) : btnBorder, 2);
    g.DrawRectangle(&borderPen, x, y, w, h);
    
    // Text
    Font btnFont(L"Segoe UI", 10, FontStyleBold);
    SolidBrush txtBr(filled ? white : txt);
    StringFormat sf; sf.SetAlignment(StringAlignmentCenter); sf.SetLineAlignment(StringAlignmentCenter);
    RectF rf((REAL)x, (REAL)y, (REAL)w, (REAL)h);
    g.DrawString(text, -1, &btnFont, rf, &sf, &txtBr);
}

void DrawCard(Graphics& g, int x, int y, int w, int h) {
    SolidBrush cardBr(card);
    g.FillRectangle(&cardBr, x, y, w, h);
    Pen borderPen(Color(42,42,74), 1);
    g.DrawRectangle(&borderPen, x, y, w, h);
}

void DrawInput(Graphics& g, int x, int y, int w, int h, const wchar_t* placeholder) {
    SolidBrush inputBg(Color(15,15,30));
    g.FillRectangle(&inputBg, x, y, w, h);
    Pen borderPen(Color(50,50,80), 1);
    g.DrawRectangle(&borderPen, x, y, w, h);
    
    Font inf(L"Segoe UI", 10);
    SolidBrush gb(gray);
    StringFormat sf; sf.SetAlignment(StringAlignmentCenter); sf.SetLineAlignment(StringAlignmentCenter);
    RectF rf((REAL)x, (REAL)y, (REAL)w, (REAL)h);
    g.DrawString(placeholder, -1, &inf, rf, &sf, &gb);
}

// ==================== TAB DEFINITIONS ====================
const wchar_t* g_tabs[] = {L"Connect", L"Devices", L"Chat", L"Stats", L"Settings", L"WOL"};
const int g_tabCount = 6;

// ==================== DRAWING ====================
void DrawTopBar(Graphics& g, int w) {
    SolidBrush topBr(Color(13,13,36));
    g.FillRectangle(&topBr, 0, 0, w, 50);
    
    Font tf(L"Segoe UI", 17, FontStyleBold);
    SolidBrush ab(accent);
    g.DrawString(L"Nexus Remote", -1, &tf, PointF(15, 10), &ab);
    
    Font uf(L"Segoe UI", 10);
    SolidBrush gn(green);
    g.DrawString((L"User: " + g_user).c_str(), -1, &uf, PointF(200, 16), &gn);
}

void DrawTabs(Graphics& g, int w) {
    int tabW = (w - 40) / g_tabCount;
    for(int i=0; i<g_tabCount; i++) {
        int x = 15 + i*(tabW+2);
        bool active = (i == g_tab);
        
        // Tab background
        SolidBrush tabBg(active ? accent : Color(26,26,46));
        g.FillRectangle(&tabBg, x, 55, tabW, 35);
        
        // Tab border
        Pen tabPen(active ? Color(129,140,248) : Color(42,42,74), active ? 2 : 1);
        g.DrawRectangle(&tabPen, x, 55, tabW, 35);
        
        // Tab text
        Font tabFont(L"Segoe UI", 9, active ? FontStyleBold : FontStyleRegular);
        SolidBrush tabTxt(active ? white : gray);
        StringFormat sf; sf.SetAlignment(StringAlignmentCenter); sf.SetLineAlignment(StringAlignmentCenter);
        RectF rf((REAL)x, 55.0f, (REAL)tabW, 35.0f);
        g.DrawString(g_tabs[i], -1, &tabFont, rf, &sf, &tabTxt);
    }
}

void DrawConnectTab(Graphics& g, int w) {
    int y = 105;
    Font h2(L"Segoe UI", 15, FontStyleBold);
    SolidBrush ab(accent);
    Font inf(L"Segoe UI", 10);
    SolidBrush gb(gray);
    
    // Card: My Device
    DrawCard(g, 15, y, w-30, 120);
    g.DrawString(L"My Device", -1, &h2, PointF(30, y+12), &ab);
    g.DrawString((L"Peer ID: " + g_peer).c_str(), -1, &inf, PointF(30, y+40), &gb);
    SolidBrush gnBr(green); g.DrawString(L"Status: Online", -1, &inf, PointF(30, y+62), &gnBr);
    
    y += 135;
    
    // Card: Connect
    DrawCard(g, 15, y, w-30, 150);
    g.DrawString(L"Connect to Device", -1, &h2, PointF(30, y+12), &ab);
    
    DrawInput(g, 30, y+45, (int)((w-60)*0.6), 32, L"Enter Peer ID...");
    DrawButton(g, 30+(int)((w-60)*0.6)+8, y+45, (int)((w-60)*0.38), 32, L"Connect", green);
    
    DrawButton(g, 30, y+90, 120, 28, L"Copy ID", accent, false);
    DrawButton(g, 160, y+90, 120, 28, L"QR Code", accent, false);
    
    y += 165;
    
    // Card: Capture
    DrawCard(g, 15, y, w-30, 100);
    g.DrawString(L"Screen Capture", -1, &h2, PointF(30, y+12), &ab);
    
    Color btnColor = g_streaming ? red : green;
    DrawButton(g, w/2-90, y+40, 180, 36, g_streaming ? L"Stop Capture" : L"Start Capture", btnColor);
}

void DrawDevicesTab(Graphics& g, int w) {
    int y = 105;
    Font h2(L"Segoe UI", 15, FontStyleBold);
    SolidBrush ab(accent);
    Font inf(L"Segoe UI", 10);
    SolidBrush gb(gray);
    
    DrawCard(g, 15, y, w-30, 80);
    g.DrawString(L"Saved Devices", -1, &h2, PointF(30, y+12), &ab);
    g.DrawString(L"No devices saved yet", -1, &inf, PointF(30, y+42), &gb);
    
    y += 95;
    
    // Demo devices
    const wchar_t* devices[] = {L"Office PC (Windows 11)", L"Gaming PC (Windows 11)", L"Laptop (macOS)"};
    const wchar_t* status[] = {L"Online", L"Sleeping", L"Online"};
    Color statColors[] = {green, orange, green};
    
    for(int i=0; i<3; i++) {
        DrawCard(g, 15, y, w-30, 60);
        g.DrawString(devices[i], -1, &h2, PointF(30, y+8), &ab);
        SolidBrush sb(statColors[i]);
        g.DrawString(status[i], -1, &inf, PointF(30, y+32), &sb);
        
        DrawButton(g, w-120, y+15, 90, 28, L"Connect", green);
        y += 75;
    }
}

void DrawChatTab(Graphics& g, int w) {
    int y = 105;
    Font h2(L"Segoe UI", 15, FontStyleBold);
    SolidBrush ab(accent);
    Font inf(L"Segoe UI", 10);
    
    DrawCard(g, 15, y, w-30, 300);
    g.DrawString(L"Chat", -1, &h2, PointF(30, y+12), &ab);
    
    // Messages
    const wchar_t* msgs[] = {L"[14:30] User1: Hello!", L"[14:31] You: Hi! How are you?", L"[14:31] User1: Great! Can you see my screen?", L"[14:32] You: Yes, perfectly!", L"[14:33] User1: Thanks for the help!"};
    Color msgColors[] = {green, accent, green, accent, green};
    
    for(int i=0; i<5; i++) {
        SolidBrush mb(msgColors[i]);
        g.DrawString(msgs[i], -1, &inf, PointF(35, y+40+i*25), &mb);
    }
    
    DrawInput(g, 30, y+260, (int)((w-60)*0.75), 30, L"Type a message...");
    DrawButton(g, 30+(int)((w-60)*0.75)+8, y+260, (int)((w-60)*0.22), 30, L"Send", accent);
}

void DrawStatsTab(Graphics& g, int w) {
    int y = 105;
    Font h2(L"Segoe UI", 15, FontStyleBold);
    SolidBrush ab(accent);
    Font inf(L"Segoe UI", 10);
    SolidBrush gb(gray);
    
    DrawCard(g, 15, y, w-30, 250);
    g.DrawString(L"Statistics", -1, &h2, PointF(30, y+12), &ab);
    
    // Stats cards
    int stats[4][2] = {{24,0},{156,0},{2048,0},{3600,0}};
    const wchar_t* statLabels[] = {L"Sessions", L"Frames Sent", L"Data (KB)", L"Duration (s)"};
    Color statColors[] = {accent, green, orange, Color(167,139,250)};
    
    for(int i=0; i<4; i++) {
        int sx = 30 + (i%2)*((w-60)/2);
        int sy = y + 45 + (i/2)*90;
        
        DrawCard(g, sx, sy, (w-60)/2-10, 75);
        Font vf(L"Segoe UI", 22, FontStyleBold);
        SolidBrush sc(statColors[i]);
        g.DrawString(std::to_wstring(stats[i][0]).c_str(), -1, &vf, PointF(sx+15, sy+10), &sc);
        g.DrawString(statLabels[i], -1, &inf, PointF(sx+15, sy+45), &gb);
    }
}

void DrawSettingsTab(Graphics& g, int w) {
    int y = 105;
    Font h2(L"Segoe UI", 15, FontStyleBold);
    SolidBrush ab(accent);
    Font inf(L"Segoe UI", 10);
    SolidBrush gb(gray);
    
    DrawCard(g, 15, y, w-30, 280);
    g.DrawString(L"Settings", -1, &h2, PointF(30, y+12), &ab);
    
    const wchar_t* settings[] = {L"Quality: High (1080p@60fps)", L"FPS: 30", L"Codec: Auto (H.264)", L"Compression: ZSTD", L"Encryption: AES-256-GCM", L"Theme: Dark"};
    
    for(int i=0; i<6; i++) {
        g.DrawString(settings[i], -1, &inf, PointF(30, y+45+i*25), &gb);
        DrawButton(g, w-120, y+38+i*25, 90, 22, L"Change", accent, false);
    }
}

void DrawWOLTab(Graphics& g, int w) {
    int y = 105;
    Font h2(L"Segoe UI", 15, FontStyleBold);
    SolidBrush ab(accent);
    Font inf(L"Segoe UI", 10);
    SolidBrush gb(gray);
    
    DrawCard(g, 15, y, w-30, 180);
    g.DrawString(L"Wake-on-LAN", -1, &h2, PointF(30, y+12), &ab);
    g.DrawString(L"Wake up your devices remotely by sending a Magic Packet", -1, &inf, PointF(30, y+38), &gb);
    
    DrawInput(g, 30, y+65, (int)((w-60)*0.6), 32, L"AA:BB:CC:DD:EE:FF");
    DrawButton(g, 30+(int)((w-60)*0.6)+8, y+65, (int)((w-60)*0.38), 32, L"Wake Up", orange);
    
    DrawButton(g, 30, y+110, w-60, 36, L"Scan Network for Devices", accent, false);
    
    y += 195;
    DrawCard(g, 15, y, w-30, 100);
    g.DrawString(L"Saved MAC Addresses", -1, &h2, PointF(30, y+12), &ab);
    g.DrawString(L"Office PC:  AA:BB:CC:DD:EE:FF", -1, &inf, PointF(30, y+40), &gb);
    g.DrawString(L"Gaming PC:  11:22:33:44:55:66", -1, &inf, PointF(30, y+60), &gb);
}

void DrawMain(HDC hdc, RECT& r) {
    Graphics g(hdc);
    g.SetSmoothingMode(SmoothingModeAntiAlias);
    g.SetTextRenderingHint(TextRenderingHintAntiAlias);
    
    int w = r.right, h = r.bottom;
    
    // Background
    SolidBrush bgBr(bg);
    g.FillRectangle(&bgBr, 0, 0, w, h);
    
    // Top bar
    DrawTopBar(g, w);
    
    // Tabs
    DrawTabs(g, w);
    
    // Tab content
    switch(g_tab) {
        case 0: DrawConnectTab(g, w); break;
        case 1: DrawDevicesTab(g, w); break;
        case 2: DrawChatTab(g, w); break;
        case 3: DrawStatsTab(g, w); break;
        case 4: DrawSettingsTab(g, w); break;
        case 5: DrawWOLTab(g, w); break;
    }
    
    // Bottom bar
    SolidBrush barBr(Color(18,18,38));
    g.FillRectangle(&barBr, 0, h-32, w, 32);
    Font bf(L"Segoe UI", 9);
    SolidBrush gb(gray);
    g.DrawString(L"Server: nexus-remote.onrender.com  |  E2E Encrypted  |  v4.0", -1, &bf, PointF(15, h-25), &gb);
}

// ==================== WINDOW PROC ====================
LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    static RECT rc;
    switch(msg) {
        case WM_SIZE:
            GetClientRect(hwnd, &rc);
            InvalidateRect(hwnd, 0, TRUE);
            break;
        case WM_PAINT: {
            PAINTSTRUCT ps; HDC hdc = BeginPaint(hwnd, &ps);
            GetClientRect(hwnd, &rc);
            DrawMain(hdc, rc);
            EndPaint(hwnd, &ps);
            break;
        }
        case WM_LBUTTONDOWN: {
            int x = LOWORD(lp), y = HIWORD(lp);
            int tabW = (rc.right - 40) / g_tabCount;
            
            // Tab click
            for(int i=0; i<g_tabCount; i++) {
                int tx = 15 + i*(tabW+2);
                if(x >= tx && x <= tx+tabW && y >= 55 && y <= 90) {
                    g_tab = i;
                    InvalidateRect(hwnd, 0, TRUE);
                    break;
                }
            }
            
            // Stream button (approximate positions)
            if(g_tab == 0 && y > 390 && y < 430) {
                g_streaming = !g_streaming;
                InvalidateRect(hwnd, 0, TRUE);
            }
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

int WINAPI WinMain(HINSTANCE hI, HINSTANCE, LPSTR, int nCS) {
    GdiplusStartupInput gdi; ULONG_PTR gdT;
    GdiplusStartup(&gdT, &gdi, NULL);
    
    WNDCLASSA wc = {};
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hI;
    wc.lpszClassName = "NexusFullUI";
    wc.hbrBackground = CreateSolidBrush(RGB(10,10,26));
    wc.hCursor = LoadCursorA(NULL, IDC_ARROW);
    RegisterClassA(&wc);
    
    HWND hwnd = CreateWindowA("NexusFullUI", "Nexus Remote v4.0 - Full UI",
        WS_OVERLAPPEDWINDOW | WS_SIZEBOX,
        CW_USEDEFAULT, CW_USEDEFAULT, 600, 700,
        NULL, NULL, hI, NULL);
    
    if(!hwnd) return 0;
    
    ShowWindow(hwnd, nCS);
    UpdateWindow(hwnd);
    
    MSG msg;
    while(GetMessageA(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageA(&msg);
    }
    
    GdiplusShutdown(gdT);
    return 0;
}


