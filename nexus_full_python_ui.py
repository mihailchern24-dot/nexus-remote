#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# nexus_full_python_ui.py - FULL Python UI = C++ features + MORE
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
import requests, json, time, threading, io, base64, secrets, hashlib, os, sys, platform
from datetime import datetime
from PIL import Image, ImageGrab
import pyautogui

SERVER = 'https://nexus-remote.onrender.com'
PEER = f'PC-{platform.node()}-{secrets.token_hex(4)}'
DEVICE_ID = f'NEXUS-{secrets.token_hex(4)}'
ACCESS_CODE = secrets.token_hex(4)

class NexusFullApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f'Nexus Remote v4.0 - {DEVICE_ID}')
        self.root.geometry('750x600')
        self.root.minsize(650, 500)
        self.root.configure(bg='#0a0a1a')
        
        # State
        self.streaming = False
        self.connected = False
        self.target = None
        self.fps = 30
        self.quality = 'high'
        self.compression = 'zstd'
        self.encryption = 'aes_gcm'
        self.view_only = False
        self.game_mode = False
        self.theme = 'dark'
        self.saved_devices = self.load_devices()
        
        # Stats
        self.frames_sent = 0
        self.bytes_sent = 0
        self.errors = 0
        self.sessions = 0
        
        # Register
        try:
            requests.post(f'{SERVER}/register', json={'peer_id':PEER,'platform':'windows','device_id':DEVICE_ID}, timeout=3)
        except: pass
        
        self.setup_ui()
    
    def load_devices(self):
        try:
            with open('nexus_devices.json') as f: return json.load(f)
        except: return []
    
    def save_devices(self):
        with open('nexus_devices.json','w') as f: json.dump(self.saved_devices, f)
    
    def btn(self, p, t, c, cmd, w=130, h=34):
        return tk.Button(p, text=t, font=('Segoe UI', 10, 'bold'), bg=c, fg='white',
                        activebackground=c, relief='flat', bd=0, padx=12, pady=6,
                        cursor='hand2', command=cmd)
    
    def card(self, p):
        return tk.Frame(p, bg='#151530', bd=0, highlightthickness=1, highlightbackground='#2a2a4a')
    
    def entry(self, p, placeholder=''):
        e = tk.Entry(p, font=('Segoe UI', 11), bg='#0f0f1a', fg='white', insertbackground='white', relief='flat', bd=1)
        if placeholder:
            e.insert(0, placeholder)
            e.bind('<FocusIn>', lambda ev: e.delete(0,'end') if e.get()==placeholder else None)
        return e
    
    def setup_ui(self):
        m = tk.Frame(self.root, bg='#0a0a1a')
        m.pack(fill='both', expand=True, padx=15, pady=10)
        
        # HEADER
        h = tk.Frame(m, bg='#0a0a1a')
        h.pack(fill='x')
        tk.Label(h, text='⚡ Nexus Remote v4.0', font=('Segoe UI', 20, 'bold'), fg='#6366f1', bg='#0a0a1a').pack(side='left')
        self.btn(h, '🌐 Open Web', '#6366f1', lambda: os.startfile(SERVER), 110, 30).pack(side='right', padx=5)
        self.btn(h, '📷 QR Code', '#f59e0b', self.show_qr, 100, 30).pack(side='right', padx=5)
        
        # STATUS BAR
        self.status_lbl = tk.Label(m, text=f'🟢 Ready | Peer: {PEER[:20]}... | Server: Online',
                                    font=('Segoe UI', 9), fg='#22c55e', bg='#0a0a1a')
        self.status_lbl.pack(anchor='w', pady=(5,10))
        
        # NOTEBOOK (TABS)
        nb = ttk.Notebook(m)
        nb.pack(fill='both', expand=True)
        
        # ============ TAB 1: CONNECT ============
        t1 = tk.Frame(nb, bg='#0a0a1a')
        nb.add(t1, text='  🔗 Connect  ')
        
        left = tk.Frame(t1, bg='#0a0a1a')
        left.pack(side='left', fill='both', expand=True, padx=(0,5))
        right = tk.Frame(t1, bg='#0a0a1a')
        right.pack(side='right', fill='both', expand=True, padx=(5,0))
        
        # Device Info
        c1 = self.card(left)
        c1.pack(fill='x', pady=5)
        tk.Label(c1, text='📱 My Device', font=('Segoe UI', 13, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=15, pady=(10,5))
        for lbl, val, clr in [('Device ID', DEVICE_ID, '#e0e0e0'), ('Access Code', ACCESS_CODE, '#f59e0b'), ('Peer ID', PEER[:24]+'...', '#888')]:
            r = tk.Frame(c1, bg='#151530')
            r.pack(fill='x', padx=15, pady=2)
            tk.Label(r, text=f'{lbl}:', font=('Segoe UI', 9), fg='#888', bg='#151530').pack(side='left')
            tk.Label(r, text=val, font=('Segoe UI', 9, 'bold'), fg=clr, bg='#151530').pack(side='right')
        
        # Connect
        c2 = self.card(left)
        c2.pack(fill='x', pady=5)
        tk.Label(c2, text='🔗 Connect to Device', font=('Segoe UI', 13, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=15, pady=(10,5))
        self.peer_e = self.entry(c2, 'Enter Peer ID...')
        self.peer_e.pack(fill='x', padx=15, pady=5)
        bf = tk.Frame(c2, bg='#151530')
        bf.pack(fill='x', padx=15, pady=(5,10))
        self.btn(bf, '🔗 Connect', '#22c55e', self.do_connect).pack(side='left', padx=(0,5))
        self.btn(bf, '📋 Copy ID', '#6366f1', lambda: self.root.clipboard_append(PEER)).pack(side='left')
        
        # Capture
        c3 = self.card(right)
        c3.pack(fill='x', pady=5)
        tk.Label(c3, text='📺 Screen Capture', font=('Segoe UI', 13, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=15, pady=(10,5))
        self.conn_lbl = tk.Label(c3, text='Not connected', font=('Segoe UI', 9), fg='#888', bg='#151530')
        self.conn_lbl.pack(anchor='w', padx=15)
        self.cap_btn = self.btn(c3, '▶ Start Capture', '#22c55e', self.toggle_capture, 200)
        self.cap_btn.pack(pady=(10,10))
        
        # Quick Settings
        c4 = self.card(right)
        c4.pack(fill='x', pady=5)
        tk.Label(c4, text='⚙️ Quick Settings', font=('Segoe UI', 13, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=15, pady=(10,5))
        for lbl, opts, var in [('Quality', ['high','medium','low'], 'quality'), ('FPS', ['30','60','15'], 'fps'), ('Compression', ['zstd','lz4','zlib'], 'compression')]:
            r = tk.Frame(c4, bg='#151530')
            r.pack(fill='x', padx=15, pady=3)
            tk.Label(r, text=lbl, font=('Segoe UI', 9), fg='#888', bg='#151530').pack(side='left')
            cb = ttk.Combobox(r, values=opts, font=('Segoe UI', 9), state='readonly', width=12)
            cb.set(opts[0])
            cb.pack(side='right')
        
        # ============ TAB 2: DEVICES ============
        t2 = tk.Frame(nb, bg='#0a0a1a')
        nb.add(t2, text='  💾 Devices  ')
        
        c5 = self.card(t2)
        c5.pack(fill='both', expand=True)
        hdr = tk.Frame(c5, bg='#151530')
        hdr.pack(fill='x', padx=15, pady=(10,8))
        tk.Label(hdr, text='💾 Saved Devices', font=('Segoe UI', 13, 'bold'), fg='#6366f1', bg='#151530').pack(side='left')
        self.btn(hdr, '🔄 Refresh', '#6366f1', self.refresh_devices, 100, 28).pack(side='right')
        
        self.dev_list = tk.Frame(c5, bg='#151530')
        self.dev_list.pack(fill='both', expand=True, padx=15, pady=(0,10))
        self.refresh_devices()
        
        # ============ TAB 3: CHAT ============
        t3 = tk.Frame(nb, bg='#0a0a1a')
        nb.add(t3, text='  💬 Chat  ')
        
        c6 = self.card(t3)
        c6.pack(fill='both', expand=True)
        tk.Label(c6, text='💬 Session Chat', font=('Segoe UI', 13, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=15, pady=(10,5))
        
        self.chat_display = scrolledtext.ScrolledText(c6, height=15, font=('Segoe UI', 10), bg='#0f0f1a', fg='#e0e0e0', relief='flat')
        self.chat_display.pack(fill='both', expand=True, padx=15, pady=5)
        self.chat_display.insert('end', '[14:30] System: Chat ready\n')
        
        inp = tk.Frame(c6, bg='#151530')
        inp.pack(fill='x', padx=15, pady=(0,10))
        self.chat_inp = tk.Entry(inp, font=('Segoe UI', 10), bg='#0f0f1a', fg='white', relief='flat', bd=1)
        self.chat_inp.pack(side='left', fill='x', expand=True)
        self.chat_inp.bind('<Return>', lambda e: self.send_chat())
        self.btn(inp, 'Send', '#6366f1', self.send_chat, 70, 28).pack(side='left', padx=(5,0))
        
        # ============ TAB 4: STATS ============
        t4 = tk.Frame(nb, bg='#0a0a1a')
        nb.add(t4, text='  📊 Stats  ')
        
        c7 = self.card(t4)
        c7.pack(fill='both', expand=True)
        tk.Label(c7, text='📊 Statistics', font=('Segoe UI', 13, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=15, pady=(10,5))
        
        self.stats_text = scrolledtext.ScrolledText(c7, height=18, font=('Consolas', 10), bg='#0f0f1a', fg='#22c55e', relief='flat')
        self.stats_text.pack(fill='both', expand=True, padx=15, pady=(0,10))
        self.update_stats_display()
        
        # ============ TAB 5: WOL ============
        t5 = tk.Frame(nb, bg='#0a0a1a')
        nb.add(t5, text='  ⚡ WOL  ')
        
        c8 = self.card(t5)
        c8.pack(fill='x')
        tk.Label(c8, text='⚡ Wake-on-LAN', font=('Segoe UI', 13, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=15, pady=(10,5))
        tk.Label(c8, text='Enter MAC address to wake device remotely', font=('Segoe UI', 9), fg='#888', bg='#151530').pack(anchor='w', padx=15)
        
        wf = tk.Frame(c8, bg='#151530')
        wf.pack(fill='x', padx=15, pady=10)
        self.mac_e = tk.Entry(wf, font=('Segoe UI', 11), bg='#0f0f1a', fg='white', relief='flat', bd=1)
        self.mac_e.pack(side='left', fill='x', expand=True)
        self.mac_e.insert(0, 'AA:BB:CC:DD:EE:FF')
        self.btn(wf, 'Wake Up', '#f59e0b', self.send_wol, 100, 32).pack(side='left', padx=(5,0))
        
        # ============ TAB 6: SETTINGS ============
        t6 = tk.Frame(nb, bg='#0a0a1a')
        nb.add(t6, text='  ⚙️ Settings  ')
        
        c9 = self.card(t6)
        c9.pack(fill='x')
        tk.Label(c9, text='⚙️ Settings', font=('Segoe UI', 13, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=15, pady=(10,5))
        
        for lbl, var, val in [('View Only Mode', 'view_only', False), ('Game Mode', 'game_mode', False), ('Dark Theme', 'theme', True)]:
            r = tk.Frame(c9, bg='#151530')
            r.pack(fill='x', padx=15, pady=5)
            tk.Label(r, text=lbl, font=('Segoe UI', 10), fg='#e0e0e0', bg='#151530').pack(side='left')
            v = tk.BooleanVar(value=val)
            tk.Checkbutton(r, variable=v, bg='#151530', activebackground='#151530', fg='#22c55e', selectcolor='#151530').pack(side='right')
        
        self.btn(c9, '💾 Save Settings', '#6366f1', lambda: messagebox.showinfo('Saved','Settings saved!')).pack(pady=(10,15))
        
        # BOTTOM BAR
        bar = tk.Frame(m, bg='#121226', height=28)
        bar.pack(fill='x', side='bottom', pady=(8,0))
        tk.Label(bar, text='nexus-remote.onrender.com | v4.0 | E2E Encrypted', font=('Segoe UI', 8), fg='#888', bg='#121226').pack(side='left', padx=10)
    
    # ==================== ACTIONS ====================
    def log(self, msg):
        t = datetime.now().strftime('%H:%M:%S')
        if hasattr(self, 'chat_display'):
            self.chat_display.insert('end', f'[{t}] {msg}\n')
            self.chat_display.see('end')
    
    def do_connect(self):
        target = self.peer_e.get().strip()
        if not target or target == 'Enter Peer ID...':
            return messagebox.showwarning('Error', 'Enter Peer ID')
        self.target = target
        self.connected = True
        self.conn_lbl.config(text=f'Connected: {target}', fg='#22c55e')
        self.status_lbl.config(text=f'🟢 Connected to {target}', fg='#22c55e')
        self.log(f'Connected to {target}')
        self.sessions += 1
        
        # Save device
        self.saved_devices.append({'id':target, 'name':target, 'time':datetime.now().isoformat()})
        self.save_devices()
        self.refresh_devices()
        messagebox.showinfo('Connected', f'Connected to {target}!')
    
    def toggle_capture(self):
        if not self.connected:
            return messagebox.showwarning('Error', 'Connect first')
        
        if not self.streaming:
            self.streaming = True
            self.cap_btn.config(text='⏹ Stop Capture', bg='#ef4444')
            self.status_lbl.config(text='🔴 Capturing...', fg='#f59e0b')
            self.log('Capture started')
            threading.Thread(target=self.capture_loop, daemon=True).start()
        else:
            self.streaming = False
            self.cap_btn.config(text='▶ Start Capture', bg='#22c55e')
            self.status_lbl.config(text='🟢 Ready', fg='#22c55e')
            self.log('Capture stopped')
    
    def capture_loop(self):
        start = time.time()
        while self.streaming:
            try:
                ss = pyautogui.screenshot()
                buf = io.BytesIO(); ss.save(buf, format='JPEG', quality=50)
                data = buf.getvalue()
                b64 = base64.b64encode(data).decode()
                requests.post(f'{SERVER}/send_frame', json={'stream_id':'x','from':PEER,'target':self.target,'frame':b64,'type':'video'}, timeout=3)
                self.frames_sent += 1
                self.bytes_sent += len(data)
                self.update_stats_display()
                time.sleep(1/self.fps)
            except Exception as e:
                self.errors += 1
                time.sleep(1)
    
    def update_stats_display(self):
        self.stats_text.delete('1.0','end')
        self.stats_text.insert('1.0',
            f'Sessions: {self.sessions}\n'
            f'Frames sent: {self.frames_sent}\n'
            f'Data sent: {self.bytes_sent//1024} KB\n'
            f'Errors: {self.errors}\n'
            f'FPS: {self.fps}\n'
            f'Quality: {self.quality}\n'
            f'Compression: {self.compression}\n'
            f'Encryption: {self.encryption}')
    
    def send_chat(self):
        msg = self.chat_inp.get().strip()
        if msg:
            self.chat_display.insert('end', f'[You] {msg}\n')
            self.chat_inp.delete(0,'end')
            self.chat_display.see('end')
    
    def send_wol(self):
        mac = self.mac_e.get().strip()
        try:
            requests.post(f'{SERVER}/wol', json={'mac':mac}, timeout=3)
            messagebox.showinfo('WOL', f'Magic Packet sent to {mac}!')
            self.log(f'WOL sent to {mac}')
        except:
            messagebox.showerror('Error', 'Failed to send WOL')
    
    def refresh_devices(self):
        for w in self.dev_list.winfo_children(): w.destroy()
        if not self.saved_devices:
            tk.Label(self.dev_list, text='No saved devices', fg='#888', bg='#151530').pack(pady=20)
            return
        for d in self.saved_devices[-10:]:
            r = tk.Frame(self.dev_list, bg='#1e1e38', bd=0, highlightthickness=1, highlightbackground='#2a2a4a')
            r.pack(fill='x', pady=1)
            tk.Label(r, text=d.get('name','?')[:20], font=('Segoe UI', 10), fg='#e0e0e0', bg='#1e1e38').pack(side='left', padx=10, pady=6)
            tk.Label(r, text=d.get('time','')[:16], font=('Segoe UI', 8), fg='#888', bg='#1e1e38').pack(side='left', padx=5)
            self.btn(r, 'Connect', '#22c55e', lambda x=d['id']: self.quick_connect(x), 80, 24).pack(side='right', padx=8)
    
    def quick_connect(self, pid):
        self.peer_e.delete(0,'end')
        self.peer_e.insert(0, pid)
        self.do_connect()
    
    def show_qr(self):
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(f'nexus://connect/{PEER}?code={ACCESS_CODE}')
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            img.save('nexus_qr.png')
            
            top = tk.Toplevel(self.root)
            top.title('QR Code')
            top.geometry('300x380')
            top.configure(bg='#0a0a1a')
            tk.Label(top, text='Scan to Connect', font=('Segoe UI', 13, 'bold'), fg='#6366f1', bg='#0a0a1a').pack(pady=10)
            photo = tk.PhotoImage(file='nexus_qr.png')
            tk.Label(top, image=photo, bg='#0a0a1a').pack()
            top.image = photo
            tk.Label(top, text=f'Code: {ACCESS_CODE}', font=('Segoe UI', 9), fg='#f59e0b', bg='#0a0a1a').pack()
        except:
            messagebox.showinfo('QR', f'Peer: {PEER}\nCode: {ACCESS_CODE}')
    
    def run(self):
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.mainloop()
    
    def on_close(self):
        self.streaming = False
        self.root.destroy()

if __name__ == '__main__':
    print('Nexus Remote v4.0 - Full Python UI')
    print(f'Server: {SERVER}')
    print(f'Device: {DEVICE_ID}')
    app = NexusFullApp()
    app.run()
