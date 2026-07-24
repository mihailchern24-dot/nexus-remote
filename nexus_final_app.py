#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests, json, time, threading, io, base64, secrets, hashlib, os, sys, platform, uuid, socket, struct, subprocess
from datetime import datetime
from PIL import Image, ImageGrab
import pyautogui

SERVER = 'https://nexus-remote.onrender.com'
PEER = f'PC-{platform.node()}-{secrets.token_hex(4)}'
DEVICE_ID = f'NEXUS-{secrets.token_hex(4)}'
ACCESS_CODE = secrets.token_hex(4)

def get_mac():
    try:
        mac = uuid.getnode()
        return ':'.join(['{:02x}'.format((mac >> (i*8)) & 0xff) for i in range(5,-1,-1)]).upper()
    except: return 'AA:BB:CC:DD:EE:FF'

LOCAL_MAC = get_mac()

class NexusApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f'Nexus Remote - {DEVICE_ID}')
        self.root.geometry('700x580')
        self.root.minsize(600, 480)
        self.root.configure(bg='#0a0a1a')
        
        self.streaming = False
        self.connected = False
        self.target = None
        self.target_mac = ''
        self.fps = 30; self.frames = 0; self.bytes = 0
        self.devices = self.load()
        
        threading.Thread(target=self.register, daemon=True).start()
        self.setup_ui()
    
    def load(self):
        try: return json.load(open('nexus_devices.json'))
        except: return []
    
    def save(self):
        json.dump(self.devices, open('nexus_devices.json','w'), indent=2)
    
    def register(self):
        try:
            requests.post(f'{SERVER}/register', json={'peer_id':PEER,'device_id':DEVICE_ID,'mac':LOCAL_MAC,'platform':'windows'}, timeout=3)
        except: pass
    
    def btn(self, p, t, c, cmd, w=110, h=32):
        return tk.Button(p, text=t, font=('Segoe UI', 9, 'bold'), bg=c, fg='white', relief='flat', bd=0, padx=8, pady=5, cursor='hand2', command=cmd)
    
    def card(self, p): return tk.Frame(p, bg='#151530', bd=0, highlightthickness=1, highlightbackground='#2a2a4a')
    
    def entry(self, p, ph=''):
        e = tk.Entry(p, font=('Segoe UI', 10), bg='#0f0f1a', fg='white', insertbackground='white', relief='flat', bd=1)
        if ph: e.insert(0, ph); e.bind('<FocusIn>', lambda ev: e.delete(0,'end') if e.get()==ph else None)
        return e
    
    def log(self, msg):
        t = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert('end', f'[{t}] {msg}\n'); self.log_text.see('end')
    
    def send_wol(self, mac):
        """Send Wake-on-LAN Magic Packet"""
        try:
            clean = mac.replace(':','').replace('-','').replace(' ','')
            if len(clean) != 12: return False
            pkt = bytes.fromhex('FF'*6 + clean*16)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(pkt, ('255.255.255.255', 9))
            s.close()
            # Also notify server
            requests.post(f'{SERVER}/wol', json={'mac':mac,'peer_id':PEER}, timeout=3)
            return True
        except Exception as e:
            self.log(f'WOL error: {e}')
            return False
    
    def setup_ui(self):
        m = tk.Frame(self.root, bg='#0a0a1a')
        m.pack(fill='both', expand=True, padx=12, pady=8)
        
        # HEADER
        h = tk.Frame(m, bg='#0a0a1a'); h.pack(fill='x')
        tk.Label(h, text='? Nexus Remote', font=('Segoe UI', 18, 'bold'), fg='#6366f1', bg='#0a0a1a').pack(side='left')
        tk.Label(h, text=f'MAC: {LOCAL_MAC}', font=('Segoe UI', 9), fg='#22c55e', bg='#0a0a1a').pack(side='right')
        
        # STATUS
        self.status_lbl = tk.Label(m, text='?? Ready', font=('Segoe UI', 9), fg='#22c55e', bg='#0a0a1a')
        self.status_lbl.pack(anchor='w', pady=(5,8))
        
        # TABS
        nb = ttk.Notebook(m); nb.pack(fill='both', expand=True)
        
        # ===== TAB 1: MY DEVICES =====
        t1 = tk.Frame(nb, bg='#0a0a1a'); nb.add(t1, text='  ?? My Devices  ')
        
        # Add device form
        c1 = self.card(t1); c1.pack(fill='x', pady=4)
        tk.Label(c1, text='? Add New Device', font=('Segoe UI', 12, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=12, pady=(8,4))
        
        r1 = tk.Frame(c1, bg='#151530'); r1.pack(fill='x', padx=12, pady=3)
        tk.Label(r1, text='Name:', font=('Segoe UI', 9), fg='#888', bg='#151530').pack(side='left')
        name_e = tk.Entry(r1, font=('Segoe UI', 10), bg='#0f0f1a', fg='white', relief='flat', bd=1, width=20)
        name_e.pack(side='left', padx=5); name_e.insert(0, 'My PC')
        
        r2 = tk.Frame(c1, bg='#151530'); r2.pack(fill='x', padx=12, pady=3)
        tk.Label(r2, text='MAC:', font=('Segoe UI', 9), fg='#888', bg='#151530').pack(side='left')
        mac_e = tk.Entry(r2, font=('Segoe UI', 10), bg='#0f0f1a', fg='white', relief='flat', bd=1, width=20)
        mac_e.pack(side='left', padx=10); mac_e.insert(0, 'AA:BB:CC:DD:EE:FF')
        
        r3 = tk.Frame(c1, bg='#151530'); r3.pack(fill='x', padx=12, pady=3)
        tk.Label(r3, text='Peer ID:', font=('Segoe UI', 9), fg='#888', bg='#151530').pack(side='left')
        peer_add_e = tk.Entry(r3, font=('Segoe UI', 10), bg='#0f0f1a', fg='white', relief='flat', bd=1, width=20)
        peer_add_e.pack(side='left', padx=5); peer_add_e.insert(0, 'Enter Peer ID...')
        
        self.btn(c1, '? Add Device', '#22c55e', lambda: self.add_device(name_e.get(), mac_e.get(), peer_add_e.get()), 140).pack(pady=(8,10))
        
        # Device list
        c2 = self.card(t1); c2.pack(fill='both', expand=True, pady=4)
        hdr = tk.Frame(c2, bg='#151530'); hdr.pack(fill='x', padx=12, pady=(8,5))
        tk.Label(hdr, text='?? My Devices', font=('Segoe UI', 12, 'bold'), fg='#6366f1', bg='#151530').pack(side='left')
        self.btn(hdr, '??', '#6366f1', self.refresh_devices, 40, 28).pack(side='right')
        
        self.dev_list = tk.Frame(c2, bg='#151530')
        self.dev_list.pack(fill='both', expand=True, padx=12, pady=(0,8))
        self.refresh_devices()
        
        # ===== TAB 2: CONNECT & STREAM =====
        t2 = tk.Frame(nb, bg='#0a0a1a'); nb.add(t2, text='  ?? Stream  ')
        
        c3 = self.card(t2); c3.pack(fill='x', pady=4)
        tk.Label(c3, text='?? Connect & Stream', font=('Segoe UI', 12, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=12, pady=(8,4))
        self.peer_e = self.entry(c3, 'Enter Peer ID...'); self.peer_e.pack(fill='x', padx=12, pady=3)
        bf = tk.Frame(c3, bg='#151530'); bf.pack(fill='x', padx=12, pady=(5,10))
        self.btn(bf, '?? Connect', '#22c55e', self.do_connect).pack(side='left', padx=(0,4))
        self.btn(bf, '? Wake & Connect', '#f59e0b', self.wake_and_connect).pack(side='left', padx=(0,4))
        self.btn(bf, '?? Copy', '#888', lambda: self.root.clipboard_append(PEER)).pack(side='left')
        
        self.conn_lbl = tk.Label(c3, text='Not connected', font=('Segoe UI', 9), fg='#888', bg='#151530')
        self.conn_lbl.pack(anchor='w', padx=12, pady=(0,5))
        
        c4 = self.card(t2); c4.pack(fill='x', pady=4)
        self.cap_btn = self.btn(c4, '? Start Capture', '#22c55e', self.toggle_capture, 200)
        self.cap_btn.pack(pady=15)
        
        # ===== TAB 3: STATS =====
        t3 = tk.Frame(nb, bg='#0a0a1a'); nb.add(t3, text='  ?? Stats  ')
        self.stats_text = scrolledtext.ScrolledText(t3, font=('Consolas', 10), bg='#0f0f1a', fg='#22c55e', relief='flat', height=20)
        self.stats_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.update_stats()
        
        # ===== TAB 4: LOG =====
        t4 = tk.Frame(nb, bg='#0a0a1a'); nb.add(t4, text='  ?? Log  ')
        self.log_text = scrolledtext.ScrolledText(t4, font=('Consolas', 9), bg='#0f0f1a', fg='#888', relief='flat', height=20)
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.log('App started')
        
        # BOTTOM
        bar = tk.Frame(m, bg='#121226', height=26); bar.pack(fill='x', side='bottom', pady=(6,0))
        tk.Label(bar, text=f'{SERVER} | v4.0 | MAC: {LOCAL_MAC}', font=('Segoe UI', 8), fg='#888', bg='#121226').pack(side='left', padx=10)
        self.btn(bar, '?? Web', '#6366f1', lambda: os.startfile(SERVER), 70, 24).pack(side='right', padx=5)
    
    # ==================== ACTIONS ====================
    def add_device(self, name, mac, peer_id):
        if not name or not mac: return messagebox.showwarning('Error', 'Name and MAC required')
        self.devices.append({'name':name, 'mac':mac.upper(), 'peer_id':peer_id if peer_id != 'Enter Peer ID...' else '', 'added':datetime.now().isoformat()})
        self.save(); self.refresh_devices()
        self.log(f'Device added: {name} ({mac})')
    
    def refresh_devices(self):
        for w in self.dev_list.winfo_children(): w.destroy()
        if not self.devices:
            tk.Label(self.dev_list, text='No devices. Add your PCs above.', fg='#888', bg='#151530').pack(pady=20)
            return
        
        for i, d in enumerate(self.devices):
            r = tk.Frame(self.dev_list, bg='#1e1e38', bd=0, highlightthickness=1, highlightbackground='#2a2a4a')
            r.pack(fill='x', pady=2)
            
            tk.Label(r, text=f'?? {d["name"]}', font=('Segoe UI', 10, 'bold'), fg='#e0e0e0', bg='#1e1e38').pack(side='left', padx=10, pady=8)
            tk.Label(r, text=f'MAC: {d["mac"]}', font=('Segoe UI', 9), fg='#22c55e', bg='#1e1e38').pack(side='left', padx=5)
            if d.get('peer_id'): tk.Label(r, text=f'Peer: {d["peer_id"][:16]}', font=('Segoe UI', 8), fg='#888', bg='#1e1e38').pack(side='left', padx=5)
            
            bf = tk.Frame(r, bg='#1e1e38'); bf.pack(side='right', padx=8)
            self.btn(bf, '? Wake', '#f59e0b', lambda x=d['mac']: self.wake_device(x), 70, 24).pack(side='left', padx=2)
            self.btn(bf, '?? Connect', '#22c55e', lambda x=d.get('peer_id',''): self.connect_to_peer(x) if x else None, 80, 24).pack(side='left', padx=2)
            self.btn(bf, '?', '#ef4444', lambda x=i: self.remove_device(x), 30, 24).pack(side='left', padx=2)
    
    def remove_device(self, idx):
        name = self.devices[idx]['name']
        self.devices.pop(idx); self.save(); self.refresh_devices()
        self.log(f'Removed: {name}')
    
    def wake_device(self, mac):
        if self.send_wol(mac):
            self.log(f'WOL sent to {mac}')
            self.status_lbl.config(text=f'? WOL sent to {mac}', fg='#f59e0b')
            messagebox.showinfo('WOL', f'Magic Packet sent!\n{mac}\n\nDevice should wake up in 30-60 seconds.\nClick Connect when ready.')
        else:
            messagebox.showerror('Error', 'Invalid MAC address')
    
    def wake_and_connect(self):
        """Wake target device then connect"""
        target = self.peer_e.get().strip()
        if not target or target == 'Enter Peer ID...':
            return messagebox.showwarning('Error', 'Enter Peer ID')
        
        # Find device by peer_id
        for d in self.devices:
            if d.get('peer_id') == target:
                self.log(f'Waking {d["name"]} ({d["mac"]})...')
                self.send_wol(d['mac'])
                self.status_lbl.config(text=f'? Waking {d["name"]}... waiting 30s', fg='#f59e0b')
                
                # Auto-connect after 35 seconds
                def delayed_connect():
                    for i in range(35, 0, -5):
                        self.status_lbl.config(text=f'? Connecting in {i}s...', fg='#f59e0b')
                        time.sleep(5)
                    self.do_connect()
                
                threading.Thread(target=delayed_connect, daemon=True).start()
                return
        
        # If no device found, just send WOL to target
        messagebox.showinfo('WOL', f'No saved MAC for {target}\n\nEnter MAC manually in My Devices tab.')
    
    def connect_to_peer(self, peer_id):
        if peer_id:
            self.peer_e.delete(0, 'end'); self.peer_e.insert(0, peer_id)
            self.do_connect()
    
    def do_connect(self):
        target = self.peer_e.get().strip()
        if not target or target == 'Enter Peer ID...': return
        
        self.target = target
        self.connected = True
        self.conn_lbl.config(text=f'Connected: {target}', fg='#22c55e')
        self.status_lbl.config(text=f'?? Connected to {target}', fg='#22c55e')
        self.log(f'Connected to {target}')
        
        # Find MAC from saved devices
        for d in self.devices:
            if d.get('peer_id') == target:
                self.target_mac = d['mac']
                self.log(f'Auto MAC: {self.target_mac}')
                break
    
    def toggle_capture(self):
        if not self.connected: return messagebox.showwarning('Error', 'Connect first')
        
        if not self.streaming:
            self.streaming = True; self.frames = 0; self.bytes = 0
            self.cap_btn.config(text='? Stop', bg='#ef4444')
            self.status_lbl.config(text='?? Capturing...', fg='#f59e0b')
            self.log('Capture started')
            threading.Thread(target=self.capture_loop, daemon=True).start()
        else:
            self.streaming = False
            self.cap_btn.config(text='? Start Capture', bg='#22c55e')
            self.status_lbl.config(text='?? Ready', fg='#22c55e')
            self.log(f'Capture stopped ({self.frames} frames, {self.bytes//1024}KB)')
    
    def capture_loop(self):
        while self.streaming:
            try:
                ss = pyautogui.screenshot()
                buf = io.BytesIO(); ss.save(buf, format='JPEG', quality=50)
                data = buf.getvalue()
                b64 = base64.b64encode(data).decode()
                requests.post(f'{SERVER}/send_frame', json={'stream_id':'x','from':PEER,'target':self.target,'frame':b64,'type':'video'}, timeout=3)
                self.frames += 1; self.bytes += len(data)
                self.update_stats()
                time.sleep(1/self.fps)
            except: time.sleep(1)
    
    def update_stats(self):
        self.stats_text.delete('1.0','end')
        self.stats_text.insert('1.0',
            f'Device: {DEVICE_ID}\nMAC: {LOCAL_MAC}\nPeer: {PEER[:20]}...\n\n'
            f'Connected: {self.target or "None"}\n'
            f'Target MAC: {self.target_mac or "Unknown"}\n\n'
            f'Frames sent: {self.frames}\n'
            f'Data sent: {self.bytes//1024} KB\n'
            f'Status: {"Streaming" if self.streaming else "Idle"}\n'
            f'FPS: {self.fps}\n'
            f'Server: {SERVER}')
    
    def run(self):
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.mainloop()
    
    def on_close(self):
        self.streaming = False; self.root.destroy()

if __name__ == '__main__':
    print(f'Nexus Remote v4.0')
    print(f'Device: {DEVICE_ID}')
    print(f'MAC: {LOCAL_MAC}')
    app = NexusApp(); app.run()

