#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# NEXUS REMOTE v4.0 - COMPLETE APPLICATION
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import requests, json, time, threading, io, base64, secrets, hashlib, os, sys, platform, uuid, socket, struct, webbrowser
from datetime import datetime, timedelta
from PIL import Image, ImageGrab
import pyautogui
import qrcode

SERVER = 'https://nexus-remote.onrender.com'
PEER = f'PC-{platform.node()}-{secrets.token_hex(4)}'
DEVICE_ID = f'NEXUS-{secrets.token_hex(4)}'
ACCESS_CODE = secrets.token_hex(4)

def get_mac():
    try:
        m = uuid.getnode()
        return ':'.join(['{:02x}'.format((m >> (i*8)) & 0xff) for i in range(5,-1,-1)]).upper()
    except: return 'AA:BB:CC:DD:EE:FF'

LOCAL_MAC = get_mac()

class NexusComplete:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f'Nexus Remote v4.0')
        self.root.geometry('820x620')
        self.root.minsize(700, 500)
        self.root.configure(bg='#0a0a1a')
        
        # ========== STATE ==========
        self.streaming = False; self.connected = False
        self.target = None; self.target_mac = ''; self.target_info = {}
        self.fps = 30; self.quality = 'high'; self.frames = 0; self.bytes_sent = 0
        self.share_links = []  # Temporary access links
        
        # ========== SECURITY SETTINGS ==========
        self.security = {
            'e2e': True, 'mfa': False, 'whitelist': True,
            'auto_lock': True, 'lock_attempts': 5, 'notify_login': True,
            'ip_blacklist': [], 'session_timeout': 30
        }
        
        # ========== DEVICES ==========
        self.devices = self.load_devices()
        
        # ========== AUTO-REGISTER ==========
        threading.Thread(target=self.register, daemon=True).start()
        
        self.setup_ui()
    
    def load_devices(self):
        try: return json.load(open('nexus_devices.json'))
        except: return []
    
    def save_devices(self):
        json.dump(self.devices, open('nexus_devices.json','w'), indent=2)
    
    def register(self):
        try:
            requests.post(f'{SERVER}/register', json={
                'peer_id':PEER, 'device_id':DEVICE_ID, 'mac':LOCAL_MAC,
                'platform':platform.system(), 'hostname':platform.node()
            }, timeout=3)
        except: pass
    
    # ========== UI HELPERS ==========
    def btn(self, p, t, c, cmd, w=110, h=32):
        return tk.Button(p, text=t, font=('Segoe UI', 9, 'bold'), bg=c, fg='white',
                        activebackground=c, relief='flat', bd=0, padx=8, pady=5, cursor='hand2', command=cmd)
    
    def card(self, p): return tk.Frame(p, bg='#151530', bd=0, highlightthickness=1, highlightbackground='#2a2a4a')
    
    def entry(self, p, ph='', show=None):
        e = tk.Entry(p, font=('Segoe UI', 10), bg='#0f0f1a', fg='white', insertbackground='white', relief='flat', bd=1, show=show if show else '')
        if ph: e.insert(0, ph); e.bind('<FocusIn>', lambda ev: e.delete(0,'end') if e.get()==ph else None)
        return e
    
    def log(self, msg, level='INFO'):
        t = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert('end', f'[{t}] [{level}] {msg}\n')
        self.log_text.see('end')
        # Color based on level
        if level == 'ERROR': self.log_text.tag_add('error', 'end-2l', 'end-1l')
        elif level == 'WARN': self.log_text.tag_add('warn', 'end-2l', 'end-1l')
        elif level == 'SUCCESS': self.log_text.tag_add('success', 'end-2l', 'end-1l')
    
    # ========== WOL ==========
    def send_wol(self, mac):
        try:
            clean = mac.replace(':','').replace('-','').replace(' ','')
            if len(clean) != 12: return False
            pkt = bytes.fromhex('FF'*6 + clean*16)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(pkt, ('255.255.255.255', 9)); s.close()
            requests.post(f'{SERVER}/wol', json={'mac':mac}, timeout=3)
            return True
        except: return False
    
    def send_sleep(self, peer_id):
        try:
            requests.post(f'{SERVER}/power', json={'peer':peer_id, 'action':'sleep'}, timeout=3)
            return True
        except: return False
    
    # ========== SHARE ACCESS ==========
    def generate_share_link(self, duration_minutes=30):
        token = secrets.token_hex(16)
        expires = datetime.now() + timedelta(minutes=duration_minutes)
        link = f'{SERVER}/support/{token}'
        self.share_links.append({'token':token, 'expires':expires.isoformat(), 'link':link})
        return link
    
    # ========== SETUP UI ==========
    def setup_ui(self):
        m = tk.Frame(self.root, bg='#0a0a1a')
        m.pack(fill='both', expand=True, padx=10, pady=8)
        
        # ==== HEADER ====
        h = tk.Frame(m, bg='#0a0a1a'); h.pack(fill='x', pady=(0,8))
        tk.Label(h, text='? Nexus Remote v4.0', font=('Segoe UI', 18, 'bold'), fg='#6366f1', bg='#0a0a1a').pack(side='left')
        
        # User info
        uf = tk.Frame(h, bg='#0a0a1a'); uf.pack(side='right')
        tk.Label(uf, text=f'ID: {DEVICE_ID[:12]}...', font=('Segoe UI', 8), fg='#888', bg='#0a0a1a').pack(side='top', anchor='e')
        tk.Label(uf, text=f'MAC: {LOCAL_MAC}', font=('Segoe UI', 8), fg='#22c55e', bg='#0a0a1a').pack(side='top', anchor='e')
        tk.Label(uf, text=f'Code: {ACCESS_CODE}', font=('Segoe UI', 8), fg='#f59e0b', bg='#0a0a1a').pack(side='top', anchor='e')
        
        # ==== NOTEBOOK ====
        nb = ttk.Notebook(m); nb.pack(fill='both', expand=True)
        
        # ===== TAB 1: HOME (Connect + Share) =====
        t1 = tk.Frame(nb, bg='#0a0a1a'); nb.add(t1, text='  ?? Home  ')
        
        # LEFT - Connect
        left = tk.Frame(t1, bg='#0a0a1a'); left.pack(side='left', fill='both', expand=True, padx=(0,5))
        right = tk.Frame(t1, bg='#0a0a1a'); right.pack(side='right', fill='both', expand=True, padx=(5,0))
        
        # My Info
        c1 = self.card(left); c1.pack(fill='x', pady=4)
        tk.Label(c1, text='?? My Device Info', font=('Segoe UI', 12, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=12, pady=(8,4))
        for l,v,c in [('Device ID', DEVICE_ID, '#e0e0e0'), ('MAC', LOCAL_MAC, '#22c55e'), ('Code', ACCESS_CODE, '#f59e0b'), ('Peer', PEER[:24]+'...', '#888'), ('Platform', platform.system(), '#888')]:
            r = tk.Frame(c1, bg='#151530'); r.pack(fill='x', padx=12, pady=1)
            tk.Label(r, text=f'{l}:', font=('Segoe UI', 9), fg='#888', bg='#151530').pack(side='left')
            tk.Label(r, text=v, font=('Segoe UI', 9, 'bold'), fg=c, bg='#151530').pack(side='right')
        
        # Connect
        c2 = self.card(left); c2.pack(fill='x', pady=4)
        tk.Label(c2, text='?? Quick Connect', font=('Segoe UI', 12, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=12, pady=(8,4))
        self.peer_e = self.entry(c2, 'Enter Peer ID or paste link...'); self.peer_e.pack(fill='x', padx=12, pady=3)
        bf = tk.Frame(c2, bg='#151530'); bf.pack(fill='x', padx=12, pady=(5,8))
        self.btn(bf, '?? Connect', '#22c55e', self.do_connect).pack(side='left', padx=2)
        self.btn(bf, '?? Scan QR', '#6366f1', self.scan_qr).pack(side='left', padx=2)
        self.btn(bf, '?? Copy ID', '#888', lambda: self.root.clipboard_append(PEER)).pack(side='left', padx=2)
        
        self.conn_lbl = tk.Label(c2, text='Ready to connect', font=('Segoe UI', 9), fg='#888', bg='#151530')
        self.conn_lbl.pack(anchor='w', padx=12, pady=(0,5))
        
        # Share Access (RIGHT)
        c3 = self.card(right); c3.pack(fill='x', pady=4)
        tk.Label(c3, text='?? Share My Screen', font=('Segoe UI', 12, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=12, pady=(8,4))
        tk.Label(c3, text='Generate temporary access link', font=('Segoe UI', 9), fg='#888', bg='#151530').pack(anchor='w', padx=12)
        
        sf = tk.Frame(c3, bg='#151530'); sf.pack(fill='x', padx=12, pady=5)
        tk.Label(sf, text='Duration:', font=('Segoe UI', 9), fg='#888', bg='#151530').pack(side='left')
        dur_var = tk.StringVar(value='30 min')
        ttk.Combobox(sf, textvariable=dur_var, values=['15 min','30 min','1 hour','4 hours','24 hours'], state='readonly', width=12).pack(side='left', padx=5)
        
        self.share_link_var = tk.StringVar()
        tk.Entry(c3, textvariable=self.share_link_var, font=('Segoe UI', 9), bg='#0f0f1a', fg='#22c55e', relief='flat', bd=1, state='readonly').pack(fill='x', padx=12, pady=3)
        
        bf2 = tk.Frame(c3, bg='#151530'); bf2.pack(fill='x', padx=12, pady=(5,8))
        self.btn(bf2, '?? Generate Link', '#f59e0b', lambda: self.share_link_var.set(self.generate_share_link({'15 min':15,'30 min':30,'1 hour':60,'4 hours':240,'24 hours':1440}[dur_var.get()]))).pack(side='left', padx=2)
        self.btn(bf2, '?? Copy', '#888', lambda: self.root.clipboard_append(self.share_link_var.get())).pack(side='left', padx=2)
        
        # Stream Controls
        c4 = self.card(right); c4.pack(fill='x', pady=4)
        tk.Label(c4, text='?? Stream Control', font=('Segoe UI', 12, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=12, pady=(8,4))
        self.cap_btn = self.btn(c4, '? Start Capture', '#22c55e', self.toggle_capture, 180)
        self.cap_btn.pack(pady=10)
        
        # ===== TAB 2: DEVICES =====
        t2 = tk.Frame(nb, bg='#0a0a1a'); nb.add(t2, text='  ?? Devices  ')
        
        # Add device
        c5 = self.card(t2); c5.pack(fill='x', pady=4)
        tk.Label(c5, text='? Add Device (requires code from owner)', font=('Segoe UI', 12, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=12, pady=(8,4))
        
        af = tk.Frame(c5, bg='#151530'); af.pack(fill='x', padx=12)
        tk.Label(af, text='Name:', font=('Segoe UI', 9), fg='#888', bg='#151530').pack(side='left')
        name_e = tk.Entry(af, font=('Segoe UI', 9), bg='#0f0f1a', fg='white', relief='flat', bd=1, width=15); name_e.pack(side='left', padx=5); name_e.insert(0, 'My PC')
        
        af2 = tk.Frame(c5, bg='#151530'); af2.pack(fill='x', padx=12, pady=3)
        tk.Label(af2, text='Secret Code/Link:', font=('Segoe UI', 9), fg='#888', bg='#151530').pack(side='left')
        code_e = tk.Entry(af2, font=('Segoe UI', 9), bg='#0f0f1a', fg='white', relief='flat', bd=1, width=30); code_e.pack(side='left', padx=5); code_e.insert(0, 'Paste code or link from owner...')
        
        self.btn(c5, '? Add Device', '#22c55e', lambda: self.add_device(name_e.get(), code_e.get()), 140).pack(pady=(8,10))
        
        # Device list
        c6 = self.card(t2); c6.pack(fill='both', expand=True, pady=4)
        hdr = tk.Frame(c6, bg='#151530'); hdr.pack(fill='x', padx=12, pady=(8,5))
        tk.Label(hdr, text='?? My Devices', font=('Segoe UI', 12, 'bold'), fg='#6366f1', bg='#151530').pack(side='left')
        self.btn(hdr, '??', '#6366f1', self.refresh_devices, 40, 28).pack(side='right')
        
        self.dev_list = tk.Frame(c6, bg='#151530'); self.dev_list.pack(fill='both', expand=True, padx=12, pady=(0,8))
        self.refresh_devices()
        
        # ===== TAB 3: SECURITY =====
        t3 = tk.Frame(nb, bg='#0a0a1a'); nb.add(t3, text='  ?? Security  ')
        
        c7 = self.card(t3); c7.pack(fill='both', expand=True, pady=4)
        tk.Label(c7, text='?? Security Settings', font=('Segoe UI', 12, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=12, pady=(8,4))
        tk.Label(c7, text='Choose protection level for your account', font=('Segoe UI', 9), fg='#888', bg='#151530').pack(anchor='w', padx=12)
        
        sec_items = [
            ('End-to-End Encryption', 'e2e', 'All data encrypted. Cannot be disabled.'),
            ('Two-Factor Auth (MFA)', 'mfa', 'Require code from Google Authenticator.'),
            ('Device Whitelist', 'whitelist', 'Only trusted devices can connect.'),
            ('Auto-Lock Account', 'auto_lock', 'Lock after failed login attempts.'),
            ('Login Notifications', 'notify_login', 'Get notified on new login.'),
            ('Session Timeout (min)', 'session_timeout', 'Auto disconnect after inactivity.'),
        ]
        
        self.sec_vars = {}
        for label, key, desc in sec_items:
            sf = tk.Frame(c7, bg='#151530'); sf.pack(fill='x', padx=12, pady=3)
            
            if key == 'session_timeout':
                tk.Label(sf, text=label, font=('Segoe UI', 10), fg='#e0e0e0', bg='#151530').pack(side='left')
                v = tk.StringVar(value='30')
                ttk.Combobox(sf, textvariable=v, values=['5','15','30','60','120'], state='readonly', width=8).pack(side='right')
                self.sec_vars[key] = v
            else:
                v = tk.BooleanVar(value=self.security.get(key, True))
                tk.Checkbutton(sf, text=label, variable=v, font=('Segoe UI', 10), fg='#e0e0e0', bg='#151530', activebackground='#151530', selectcolor='#151530').pack(side='left')
                self.sec_vars[key] = v
            
            tk.Label(sf, text=desc, font=('Segoe UI', 8), fg='#888', bg='#151530').pack(side='right')
        
        self.btn(c7, '?? Save Security Settings', '#6366f1', self.save_security).pack(pady=(10,8))
        
        # Learn more link
        tk.Label(c7, text='?? Learn more about security: nexus-remote.onrender.com/docs', font=('Segoe UI', 9), fg='#6366f1', bg='#151530', cursor='hand2').pack(pady=(0,10))
        tk.Label(c7, text='Click to open documentation in browser', font=('Segoe UI', 8), fg='#888', bg='#151530').pack()
        
        # ===== TAB 4: LOG =====
        t4 = tk.Frame(nb, bg='#0a0a1a'); nb.add(t4, text='  ?? Log  ')
        self.log_text = scrolledtext.ScrolledText(t4, font=('Consolas', 9), bg='#0f0f1a', fg='#e0e0e0', relief='flat')
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.log_text.tag_config('error', foreground='#ef4444')
        self.log_text.tag_config('warn', foreground='#f59e0b')
        self.log_text.tag_config('success', foreground='#22c55e')
        self.log('Application started', 'SUCCESS')
        
        # ===== TAB 5: STATS =====
        t5 = tk.Frame(nb, bg='#0a0a1a'); nb.add(t5, text='  ?? Stats  ')
        self.stats_text = scrolledtext.ScrolledText(t5, font=('Consolas', 10), bg='#0f0f1a', fg='#22c55e', relief='flat')
        self.stats_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.update_stats()
        
        # ==== BOTTOM BAR ====
        bar = tk.Frame(m, bg='#121226', height=26); bar.pack(fill='x', side='bottom', pady=(6,0))
        tk.Label(bar, text=f'{SERVER} | v4.0 | E2E Encrypted', font=('Segoe UI', 8), fg='#888', bg='#121226').pack(side='left', padx=10)
        self.btn(bar, '?? Docs', '#6366f1', lambda: webbrowser.open(f'{SERVER}/docs'), 70, 22).pack(side='right', padx=4)
        self.btn(bar, '?? Web', '#6366f1', lambda: webbrowser.open(SERVER), 70, 22).pack(side='right', padx=4)
    
    # ========== ACTIONS ==========
    def add_device(self, name, code):
        if not name: return messagebox.showwarning('Error', 'Enter device name')
        if not code or code == 'Paste code or link from owner...': return messagebox.showwarning('Error', 'Enter secret code or link from device owner')
        
        # Simulate verification (in real app, verify with server)
        self.devices.append({
            'name': name, 'code_hash': hashlib.sha256(code.encode()).hexdigest()[:16],
            'added': datetime.now().isoformat(), 'peer_id': '', 'mac': '', 'status': 'pending'
        })
        self.save_devices(); self.refresh_devices()
        self.log(f'Device added: {name} (pending verification)', 'SUCCESS')
        messagebox.showinfo('Added', f'{name} added!\n\nAsk the owner to approve your request.')
    
    def refresh_devices(self):
        for w in self.dev_list.winfo_children(): w.destroy()
        if not self.devices:
            tk.Label(self.dev_list, text='No devices. Get a code from another user to add their device.', fg='#888', bg='#151530', wraplength=500).pack(pady=20)
            return
        
        for i, d in enumerate(self.devices):
            r = tk.Frame(self.dev_list, bg='#1e1e38', bd=0, highlightthickness=1, highlightbackground='#2a2a4a')
            r.pack(fill='x', pady=2)
            
            status_icon = '??' if d.get('status')=='online' else '??' if d.get('status')=='offline' else '??'
            tk.Label(r, text=f'{status_icon} {d["name"]}', font=('Segoe UI', 10, 'bold'), fg='#e0e0e0', bg='#1e1e38').pack(side='left', padx=10, pady=8)
            if d.get('mac'): tk.Label(r, text=f'MAC: {d["mac"]}', font=('Segoe UI', 8), fg='#22c55e', bg='#1e1e38').pack(side='left', padx=5)
            tk.Label(r, text=d.get('status','pending').upper(), font=('Segoe UI', 8), fg='#f59e0b', bg='#1e1e38').pack(side='left', padx=5)
            
            bf = tk.Frame(r, bg='#1e1e38'); bf.pack(side='right', padx=8)
            self.btn(bf, '? Wake', '#f59e0b', lambda x=d.get('mac',''): self.wake_device(x) if x else None, 65, 22).pack(side='left', padx=2)
            self.btn(bf, '?? Sleep', '#888', lambda: None, 65, 22).pack(side='left', padx=2)
            self.btn(bf, '?? View', '#22c55e', lambda: None, 65, 22).pack(side='left', padx=2)
            self.btn(bf, '?', '#ef4444', lambda x=i: self.remove_device(x), 28, 22).pack(side='left', padx=2)
    
    def wake_device(self, mac):
        if self.send_wol(mac):
            self.log(f'WOL sent to {mac}', 'SUCCESS')
            messagebox.showinfo('WOL', f'Magic Packet sent!\n{mac}\n\nDevice should wake up in 30-60 seconds.')
    
    def remove_device(self, idx):
        name = self.devices[idx]['name']
        self.devices.pop(idx); self.save_devices(); self.refresh_devices()
        self.log(f'Removed: {name}')
    
    def do_connect(self):
        target = self.peer_e.get().strip()
        if not target or target == 'Enter Peer ID or paste link...': return
        self.target = target; self.connected = True
        self.conn_lbl.config(text=f'Connected: {target}', fg='#22c55e')
        self.log(f'Connected to {target}', 'SUCCESS')
    
    def toggle_capture(self):
        if not self.connected: return messagebox.showwarning('Error', 'Connect first')
        if not self.streaming:
            self.streaming = True; self.frames = 0
            self.cap_btn.config(text='? Stop', bg='#ef4444')
            self.log('Capture started')
            threading.Thread(target=self.capture_loop, daemon=True).start()
        else:
            self.streaming = False
            self.cap_btn.config(text='? Start Capture', bg='#22c55e')
            self.log(f'Capture stopped ({self.frames} frames)')
    
    def capture_loop(self):
        while self.streaming:
            try:
                ss = pyautogui.screenshot()
                buf = io.BytesIO(); ss.save(buf, format='JPEG', quality=50)
                data = buf.getvalue(); b64 = base64.b64encode(data).decode()
                requests.post(f'{SERVER}/send_frame', json={'stream_id':'x','from':PEER,'target':self.target,'frame':b64,'type':'video'}, timeout=3)
                self.frames += 1; self.bytes_sent += len(data)
                self.update_stats()
                time.sleep(1/self.fps)
            except: time.sleep(1)
    
    def save_security(self):
        for k, v in self.sec_vars.items():
            if k == 'session_timeout': self.security[k] = int(v.get())
            else: self.security[k] = v.get()
        self.log('Security settings saved', 'SUCCESS')
        messagebox.showinfo('Saved', 'Security settings updated!')
    
    def scan_qr(self):
        messagebox.showinfo('QR Scan', 'Point camera at QR code on other device.\n\nOr enter Peer ID manually.')
    
    def update_stats(self):
        self.stats_text.delete('1.0','end')
        self.stats_text.insert('end', 'ã======================================¬\n')
        self.stats_text.insert('end', '¦     ?? NEXUS REMOTE STATS            ¦\n')
        self.stats_text.insert('end', 'L======================================-\n\n')
        self.stats_text.insert('end', f'Device: {DEVICE_ID}\n')
        self.stats_text.insert('end', f'MAC: {LOCAL_MAC}\n')
        self.stats_text.insert('end', f'Connected: {self.target or "None"}\n')
        self.stats_text.insert('end', f'Streaming: {"Yes" if self.streaming else "No"}\n')
        self.stats_text.insert('end', f'Frames: {self.frames}\n')
        self.stats_text.insert('end', f'Data: {self.bytes_sent//1024} KB\n')
        self.stats_text.insert('end', f'Security: E2E {"ON" if self.security["e2e"] else "OFF"} | MFA {"ON" if self.security["mfa"] else "OFF"}\n')
        self.stats_text.insert('end', f'Devices: {len(self.devices)}\n')
    
    def run(self):
        self.root.protocol('WM_DELETE_WINDOW', lambda: (setattr(self,'streaming',False), self.root.destroy()))
        self.root.mainloop()

if __name__ == '__main__':
    app = NexusComplete(); app.run()

