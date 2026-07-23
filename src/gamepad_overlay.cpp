// gamepad_overlay.cpp - Virtual Gamepad for Nexus Remote
// Compile: g++ -o gamepad_demo.exe gamepad_overlay.cpp -lgdiplus -mwindows -std=c++17
#include <windows.h>
#include <gdiplus.h>
#include <string>
#pragma comment(lib, "gdiplus.lib")
using namespace Gdiplus;
using std::min;

// ==================== GAMEPAD STATE ====================
bool g_gamepad_visible = true;
bool g_gamepad_enabled = true;
bool g_auto_hide = true;
int g_gamepad_alpha = 180; // 0-255 transparency
float g_gamepad_scale = 1.0f;

// Button states
bool g_btn_a = false, g_btn_b = false, g_btn_x = false, g_btn_y = false;
bool g_dpad_up = false, g_dpad_down = false, g_dpad_left = false, g_dpad_right = false;
bool g_lb = false, g_rb = false, g_lt = false, g_rt = false;
bool g_start = false, g_select = false;
float g_lstick_x = 0, g_lstick_y = 0;
float g_rstick_x = 0, g_rstick_y = 0;

// Colors
Color bg(10,10,26), accent(99,102,241), green(34,197,94);
Color red(239,68,68), orange(245,158,11), white(255,255,255);
Color gray(136,136,160), btnColor(40,40,60);
Color btnActive(99,102,241);

// ==================== DRAWING ====================
void DrawCircle(Graphics& g, float cx, float cy, float r, Color color, bool filled=true) {
    if(filled) { SolidBrush b(color); g.FillEllipse(&b, cx-r, cy-r, r*2, r*2); }
    else { Pen p(color, 2); g.DrawEllipse(&p, cx-r, cy-r, r*2, r*2); }
}

void DrawRoundRect(Graphics& g, float x, float y, float w, float h, float r, Color color, bool filled=true) {
    GraphicsPath path;
    path.AddArc(x, y, r*2, r*2, 180, 90);
    path.AddArc(x+w-r*2, y, r*2, r*2, 270, 90);
    path.AddArc(x+w-r*2, y+h-r*2, r*2, r*2, 0, 90);
    path.AddArc(x, y+h-r*2, r*2, r*2, 90, 90);
    path.CloseFigure();
    if(filled) { SolidBrush b(color); g.FillPath(&b, &path); }
    else { Pen p(color, 2); g.DrawPath(&p, &path); }
}

void DrawGamepadButton(Graphics& g, float x, float y, float w, float h, const wchar_t* text, bool pressed, Color normalColor) {
    Color c = pressed ? btnActive : normalColor;
    DrawRoundRect(g, x, y, w, h, 8, c);
    
    Font f(L"Segoe UI", 12, FontStyleBold);
    SolidBrush tb(white);
    StringFormat sf; sf.SetAlignment(StringAlignmentCenter); sf.SetLineAlignment(StringAlignmentCenter);
    g.DrawString(text, -1, &f, RectF(x, y, w, h), &sf, &tb);
}

void DrawGamepad(Graphics& g, int screenW, int screenH) {
    if(!g_gamepad_visible || !g_gamepad_enabled) return;
    
    // Gamepad background (semi-transparent)
    float gw = 500 * g_gamepad_scale;
    float gh = 320 * g_gamepad_scale;
    float gx = (screenW - gw) / 2;
    float gy = screenH - gh - 20;
    
    // Main body
    Color bgAlpha(g_gamepad_alpha, 20, 20, 40);
    DrawRoundRect(g, gx, gy, gw, gh, 25, bgAlpha);
    
    // Title
    Font titleF(L"Segoe UI", 10, FontStyleBold);
    SolidBrush gb(gray);
    StringFormat sf; sf.SetAlignment(StringAlignmentCenter);
    g.DrawString(L"Virtual Gamepad", -1, &titleF, RectF(gx, gy-20, gw, 20), &sf, &gb);
    
    // D-Pad (Left)
    float dpad_cx = gx + 90 * g_gamepad_scale;
    float dpad_cy = gy + gh/2 - 20;
    float dpad_size = 25 * g_gamepad_scale;
    
    DrawGamepadButton(g, dpad_cx-dpad_size, dpad_cy-dpad_size*2, dpad_size*2, dpad_size*2, L"?", g_dpad_up, btnColor);
    DrawGamepadButton(g, dpad_cx-dpad_size, dpad_cy+dpad_size, dpad_size*2, dpad_size*2, L"?", g_dpad_down, btnColor);
    DrawGamepadButton(g, dpad_cx-dpad_size*2.5f, dpad_cy-dpad_size, dpad_size*2, dpad_size*2, L"?", g_dpad_left, btnColor);
    DrawGamepadButton(g, dpad_cx+dpad_size*0.5f, dpad_cy-dpad_size, dpad_size*2, dpad_size*2, L"?", g_dpad_right, btnColor);
    
    // Left Stick
    float ls_cx = gx + 90 * g_gamepad_scale;
    float ls_cy = gy + gh/2 - 20;
    DrawCircle(g, ls_cx + g_lstick_x * 20, ls_cy + g_lstick_y * 20, 22 * g_gamepad_scale, Color(60,60,80));
    DrawCircle(g, ls_cx + g_lstick_x * 20, ls_cy + g_lstick_y * 20, 12 * g_gamepad_scale, Color(80,80,100));
    
    // ABXY Buttons (Right)
    float btn_cx = gx + gw - 100 * g_gamepad_scale;
    float btn_cy = gy + gh/2 - 30;
    float btn_size = 22 * g_gamepad_scale;
    
    DrawGamepadButton(g, btn_cx, btn_cy-btn_size*1.5f, btn_size*2, btn_size*2, L"Y", g_btn_y, Color(180,180,40));
    DrawGamepadButton(g, btn_cx-btn_size*1.5f, btn_cy, btn_size*2, btn_size*2, L"X", g_btn_x, Color(40,100,180));
    DrawGamepadButton(g, btn_cx+btn_size*1.5f, btn_cy, btn_size*2, btn_size*2, L"B", g_btn_b, Color(180,40,40));
    DrawGamepadButton(g, btn_cx, btn_cy+btn_size*1.5f, btn_size*2, btn_size*2, L"A", g_btn_a, Color(40,180,80));
    
    // Right Stick
    float rs_cx = gx + gw - 100 * g_gamepad_scale;
    float rs_cy = gy + gh/2 - 30;
    DrawCircle(g, rs_cx + g_rstick_x * 20, rs_cy + g_rstick_y * 20, 18 * g_gamepad_scale, Color(60,60,80));
    DrawCircle(g, rs_cx + g_rstick_x * 20, rs_cy + g_rstick_y * 20, 10 * g_gamepad_scale, Color(80,80,100));
    
    // Bumpers & Triggers
    DrawGamepadButton(g, gx+20, gy-10, 80*g_gamepad_scale, 18*g_gamepad_scale, L"LB", g_lb, btnColor);
    DrawGamepadButton(g, gx+gw-100*g_gamepad_scale, gy-10, 80*g_gamepad_scale, 18*g_gamepad_scale, L"RB", g_rb, btnColor);
    DrawGamepadButton(g, gx+10, gy-30, 60*g_gamepad_scale, 18*g_gamepad_scale, L"LT", g_lt, btnColor);
    DrawGamepadButton(g, gx+gw-70*g_gamepad_scale, gy-30, 60*g_gamepad_scale, 18*g_gamepad_scale, L"RT", g_rt, btnColor);
    
    // Start/Select
    float mid_x = gx + gw/2;
    DrawGamepadButton(g, mid_x-40, gy+gh-30, 30*g_gamepad_scale, 20*g_gamepad_scale, L"?", g_select, btnColor);
    DrawGamepadButton(g, mid_x+10, gy+gh-30, 30*g_gamepad_scale, 20*g_gamepad_scale, L"?", g_start, btnColor);
}

// ==================== MAIN WINDOW ====================
LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    static RECT rc;
    switch(msg) {
        case WM_SIZE:
            GetClientRect(hwnd, &rc);
            InvalidateRect(hwnd, 0, 1);
            break;
        case WM_PAINT: {
            PAINTSTRUCT ps; HDC hdc = BeginPaint(hwnd, &ps);
            GetClientRect(hwnd, &rc);
            Graphics g(hdc);
            g.SetSmoothingMode(SmoothingModeAntiAlias);
            
            // Background
            SolidBrush bgBr(bg);
            g.FillRectangle(&bgBr, 0, 0, rc.right, rc.bottom);
            
            // Draw gamepad
            DrawGamepad(g, rc.right, rc.bottom);
            
            // Controls panel
            Font f(L"Segoe UI", 11);
            SolidBrush wb(white);
            SolidBrush gb(gray);
            
            g.DrawString(L"Gamepad Controls:", -1, &f, PointF(15, 10), &wb);
            
            const wchar_t* controls[] = {
                L"WASD / Arrows = D-Pad",
                L"Enter = A | Space = B | Q = X | E = Y",
                L"Shift = LB | Ctrl = RB | Tab = Select | Esc = Start",
                L"Mouse = Right Stick | G = Toggle Gamepad | H = Hide/Show"
            };
            Font cf(L"Segoe UI", 9);
            for(int i=0; i<4; i++) {
                g.DrawString(controls[i], -1, &cf, PointF(15, 35 + i*20), &gb);
            }
            
            EndPaint(hwnd, &ps);
            break;
        }
        case WM_KEYDOWN: {
            bool handled = true;
            switch(wp) {
                case 'W': g_dpad_up = true; break;
                case 'S': g_dpad_down = true; break;
                case 'A': g_dpad_left = true; break;
                case 'D': g_dpad_right = true; break;
                case VK_UP: g_dpad_up = true; break;
                case VK_DOWN: g_dpad_down = true; break;
                case VK_LEFT: g_dpad_left = true; break;
                case VK_RIGHT: g_dpad_right = true; break;
                case VK_RETURN: g_btn_a = true; break;
                case VK_SPACE: g_btn_b = true; break;
                case 'Q': g_btn_x = true; break;
                case 'E': g_btn_y = true; break;
                case VK_SHIFT: g_lb = true; break;
                case VK_CONTROL: g_rb = true; break;
                case VK_TAB: g_select = true; break;
                case VK_ESCAPE: g_start = true; break;
                case 'G': g_gamepad_enabled = !g_gamepad_enabled; break;
                case 'H': g_gamepad_visible = !g_gamepad_visible; break;
                default: handled = false;
            }
            if(handled) InvalidateRect(hwnd, 0, 1);
            break;
        }
        case WM_KEYUP: {
            switch(wp) {
                case 'W': g_dpad_up = false; break;
                case 'S': g_dpad_down = false; break;
                case 'A': g_dpad_left = false; break;
                case 'D': g_dpad_right = false; break;
                case VK_UP: g_dpad_up = false; break;
                case VK_DOWN: g_dpad_down = false; break;
                case VK_LEFT: g_dpad_left = false; break;
                case VK_RIGHT: g_dpad_right = false; break;
                case VK_RETURN: g_btn_a = false; break;
                case VK_SPACE: g_btn_b = false; break;
                case 'Q': g_btn_x = false; break;
                case 'E': g_btn_y = false; break;
                case VK_SHIFT: g_lb = false; break;
                case VK_CONTROL: g_rb = false; break;
                case VK_TAB: g_select = false; break;
                case VK_ESCAPE: g_start = false; break;
            }
            InvalidateRect(hwnd, 0, 1);
            break;
        }
        case WM_MOUSEMOVE: {
            g_rstick_x = (LOWORD(lp) - rc.right/2) / 100.0f;
            g_rstick_y = (HIWORD(lp) - rc.bottom/2) / 100.0f;
            InvalidateRect(hwnd, 0, 1);
            break;
        }
        case WM_LBUTTONDOWN: g_lt = true; InvalidateRect(hwnd, 0, 1); break;
        case WM_LBUTTONUP: g_lt = false; InvalidateRect(hwnd, 0, 1); break;
        case WM_RBUTTONDOWN: g_rt = true; InvalidateRect(hwnd, 0, 1); break;
        case WM_RBUTTONUP: g_rt = false; InvalidateRect(hwnd, 0, 1); break;
        case WM_DESTROY: PostQuitMessage(0); break;
        default: return DefWindowProcA(hwnd, msg, wp, lp);
    }
    return 0;
}

int WINAPI WinMain(HINSTANCE i, HINSTANCE, LPSTR, int c) {
    GdiplusStartupInput g; ULONG_PTR t; GdiplusStartup(&t, &g, 0);
    
    WNDCLASSA wc = {};
    wc.lpfnWndProc = WndProc; wc.hInstance = i;
    wc.lpszClassName = "NexusGamepad";
    wc.hbrBackground = CreateSolidBrush(RGB(10,10,26));
    wc.hCursor = LoadCursorA(0, IDC_ARROW);
    RegisterClassA(&wc);
    
    HWND h = CreateWindowA("NexusGamepad", "Nexus Remote - Virtual Gamepad Demo",
        WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 700, 550, 0, 0, i, 0);
    
    ShowWindow(h, c); UpdateWindow(h);
    
    MSG m;
    while(GetMessageA(&m, 0, 0, 0)) { TranslateMessage(&m); DispatchMessageA(&m); }
    
    GdiplusShutdown(t);
    return 0;
}
