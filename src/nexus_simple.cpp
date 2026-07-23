#include <windows.h>
#include <gdiplus.h>
#include <string>
#pragma comment(lib, "gdiplus.lib")
using namespace Gdiplus;

bool g_logged_in = false;
std::wstring g_user = L"demo@nexus.com";

void DrawLogin(HDC hdc, RECT& r) {
    Graphics g(hdc);
    SolidBrush bg(Color(10,10,26)); g.FillRectangle(&bg,0,0,r.right,r.bottom);
    Font f(L"Segoe UI",28,FontStyleBold);
    SolidBrush ab(Color(99,102,241));
    g.DrawString(L"Nexus Remote",-1,&f,PointF(r.right/2-120,40),&ab);
    Font f2(L"Segoe UI",12);
    SolidBrush gb(Color(136,136,160));
    g.DrawString(L"Secure Remote Desktop & Streaming",-1,&f2,PointF(r.right/2-140,80),&gb);
    Font f3(L"Segoe UI",14);
    g.DrawString(L"Login: demo@nexus.com",-1,&f3,PointF(r.right/2-100,160),&gb);
    g.DrawString(L"Password: demo123456",-1,&f3,PointF(r.right/2-100,190),&gb);
    SolidBrush gn(Color(34,197,94));
    g.DrawString(L"Click anywhere to login",-1,&f3,PointF(r.right/2-100,240),&gn);
}

void DrawMain(HDC hdc, RECT& r) {
    Graphics g(hdc);
    SolidBrush bg(Color(10,10,26)); g.FillRectangle(&bg,0,0,r.right,r.bottom);
    SolidBrush tb(Color(13,13,36)); g.FillRectangle(&tb,0,0,r.right,50);
    Font f(L"Segoe UI",18,FontStyleBold);
    SolidBrush ab(Color(99,102,241));
    g.DrawString(L"Nexus Remote",-1,&f,PointF(15,12),&ab);
    Font f2(L"Segoe UI",11);
    SolidBrush gn(Color(34,197,94));
    g.DrawString((L"User: "+g_user).c_str(),-1,&f2,PointF(200,16),&gn);
    
    SolidBrush card(Color(21,21,48));
    int y=70, cw=r.right-30;
    
    g.FillRectangle(&card,15,y,cw,140);
    Font h2(L"Segoe UI",16,FontStyleBold);
    g.DrawString(L"Connect to Device",-1,&h2,PointF(30,y+15),&ab);
    Font inf(L"Segoe UI",11);
    SolidBrush gb(Color(136,136,160));
    g.DrawString(L"Peer ID: nexus-129025594271",-1,&inf,PointF(30,y+45),&gb);
    g.DrawString(L"Enter Peer ID to connect",-1,&inf,PointF(30,y+70),&gb);
    
    y+=160;
    g.FillRectangle(&card,15,y,cw,110);
    g.DrawString(L"Streaming Control",-1,&h2,PointF(30,y+15),&ab);
    SolidBrush sb(Color(136,136,160));
    g.DrawString(L"Status: Ready",-1,&inf,PointF(30,y+45),&sb);
    
    y+=130;
    g.FillRectangle(&card,15,y,cw,90);
    g.DrawString(L"Wake-on-LAN",-1,&h2,PointF(30,y+15),&ab);
    g.DrawString(L"MAC: AA:BB:CC:DD:EE:FF",-1,&inf,PointF(30,y+45),&gb);
    
    Font lf(L"Segoe UI",9);
    g.DrawString(L"Click to logout",-1,&lf,PointF(r.right-120,r.bottom-30),&gb);
}

LRESULT CALLBACK WndProc(HWND h,UINT m,WPARAM w,LPARAM l){
    static RECT rc;
    switch(m){
        case WM_SIZE: GetClientRect(h,&rc); InvalidateRect(h,0,1); break;
        case WM_PAINT:{ PAINTSTRUCT p; HDC d=BeginPaint(h,&p); GetClientRect(h,&rc);
            g_logged_in?DrawMain(d,rc):DrawLogin(d,rc); EndPaint(h,&p); break;}
        case WM_LBUTTONDOWN: g_logged_in=!g_logged_in; InvalidateRect(h,0,1); break;
        case WM_DESTROY: PostQuitMessage(0); break;
        default: return DefWindowProcA(h,m,w,l);
    }
    return 0;
}

int WINAPI WinMain(HINSTANCE i,HINSTANCE,LPSTR,int c){
    GdiplusStartupInput g; ULONG_PTR t; GdiplusStartup(&t,&g,0);
    WNDCLASSA wc={}; wc.lpfnWndProc=WndProc; wc.hInstance=i;
    wc.lpszClassName="NexusSimple"; wc.hCursor=LoadCursorA(0,IDC_ARROW);
    RegisterClassA(&wc);
    HWND h=CreateWindowA("NexusSimple","Nexus Remote v4.0",WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT,CW_USEDEFAULT,500,600,0,0,i,0);
    ShowWindow(h,c); UpdateWindow(h);
    MSG m; while(GetMessageA(&m,0,0,0)){TranslateMessage(&m);DispatchMessageA(&m);}
    GdiplusShutdown(t); return 0;
}
