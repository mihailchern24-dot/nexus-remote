#!/usr/bin/env python3
# nexus_client_final.py - Nexus Remote Client v4.0
# QR-код доступен только после ввода пароля устройства
import requests
import json
import time
import base64
import threading
import os
import sys
import platform
import io
import secrets
import sqlite3
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from datetime import datetime
from PIL import Image, ImageDraw
import pyautogui
import qrcode

# ==================== КОНФИГУРАЦИЯ ====================
SERVER_URL = "https://nexus-remote.onrender.com"
WEB_URL = "https://nexus-remote.onrender.com"
COMPRESSION = "zstd"
ENCRYPTION = "aes_gcm"
DB_FILE = "nexus_client.db"

class NexusClient:
    def __init__(self):
        self.peer_id = f"PC-{platform.node()}-{secrets.token_hex(4)}"
        self.stream_id = None
        self.connected_peer = None
        self.capturing = False
        self.fps = 30
        self.quality = "high"
        self.device_id = f"NEXUS-{secrets.token_hex(4)}"
        self.access_code = secrets.token_hex(4)
        self.password_hash = hashlib.sha256(self.access_code.encode()).hexdigest()
        
        self.db = sqlite3.connect(DB_FILE, check_same_thread=False)
        self._init_db()
        
        self.stats = {'frames': 0, 'bytes': 0, 'errors': 0, 'start_time': None}
    
    def _init_db(self):
        c = self.db.cursor()
        c.executescript('''
            CREATE TABLE IF NOT EXISTS devices (
                peer_id TEXT PRIMARY KEY, name TEXT, platform TEXT,
                last_connected TEXT, is_favorite INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                peer_id TEXT, date TEXT, frames INTEGER,
                bytes INTEGER, duration INTEGER, fps REAL
            );
        ''')
        self.db.commit()
    
    def verify_access(self, code):
        return hashlib.sha256(code.encode()).hexdigest() == self.password_hash
    
    def register(self):
        try:
            data = {"peer_id": self.peer_id, "platform": "windows", "device_id": self.device_id,
                    "access_code": self.access_code, "compression": COMPRESSION, "encryption": ENCRYPTION}
            resp = requests.post(f"{SERVER_URL}/register", json=data, timeout=5)
            return resp.json().get('status') == 'registered'
        except:
            return False
    
    def start_stream(self, target):
        data = {"source": self.peer_id, "target": target, "quality": self.quality}
        try:
            resp = requests.post(f"{SERVER_URL}/start_stream", json=data, timeout=5)
            if resp.json().get('status') == 'streaming':
                self.stream_id = resp.json()['stream_id']
                self.connected_peer = target
                self.stats['start_time'] = time.time()
                c = self.db.cursor()
                c.execute('INSERT OR REPLACE INTO devices (peer_id, name, last_connected) VALUES (?, ?, ?)',
                         (target, target, datetime.now().isoformat()))
                self.db.commit()
                return True, "Connected"
        except Exception as e:
            pass
        return False, "Failed"
    
    def send_frame(self, frame_bytes):
        if not self.stream_id: return
        try:
            frame_b64 = base64.b64encode(frame_bytes).decode()
            data = {"stream_id": self.stream_id, "from": self.peer_id, "target": self.connected_peer, "frame": frame_b64, "type": "video"}
            requests.post(f"{SERVER_URL}/send_frame", json=data, timeout=5)
            self.stats['frames'] += 1
            self.stats['bytes'] += len(frame_bytes)
        except:
            self.stats['errors'] += 1
    
    def stop_stream(self):
        if self.stream_id:
            duration = int(time.time() - self.stats['start_time']) if self.stats['start_time'] else 0
            c = self.db.cursor()
            c.execute('INSERT INTO stats (peer_id, date, frames, bytes, duration, fps) VALUES (?, ?, ?, ?, ?, ?)',
                     (self.connected_peer, datetime.now().isoformat(), self.stats['frames'], 
                      self.stats['bytes'], duration, self.fps))
            self.db.commit()
            try:
                requests.post(f"{SERVER_URL}/stop_stream", json={"stream_id": self.stream_id}, timeout=3)
            except:
                pass
            self.stream_id = None
            self.connected_peer = None
    
    def get_peers(self):
        try:
            resp = requests.get(f"{SERVER_URL}/peers", timeout=3)
            return resp.json().get('peers', [])
        except:
            return []
    
    def get_saved_devices(self):
        c = self.db.cursor()
        c.execute('SELECT * FROM devices ORDER BY last_connected DESC')
        return c.fetchall()
    
    def update_device_name(self, peer_id, name):
        c = self.db.cursor()
        c.execute('UPDATE devices SET name=? WHERE peer_id=?', (name, peer_id))
        self.db.commit()
    
    def get_stats(self):
        c = self.db.cursor()
        c.execute('SELECT peer_id, SUM(frames), SUM(bytes), SUM(duration), AVG(fps) FROM stats GROUP BY peer_id')
        return c.fetchall()
    
    def generate_qr_data(self):
        return f"nexus://connect/{self.peer_id}?device={self.device_id}&code={self.access_code}"

# ==================== UI ====================
class NexusUI:
    def __init__(self):
        self.client = NexusClient()
        self.root = tk.Tk()
        self.root.title(f"Nexus Remote - {self.client.device_id}")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        self.bg = '#0a0a1a'
        self.card = '#151530'
        self.accent = '#6366f1'
        self.green = '#22c55e'
        self.red = '#ef4444'
        self.orange = '#f59e0b'
        self.text = '#e0e0e0'
        self.gray = '#888'
        
        self.root.configure(bg=self.bg)
        
        # Показываем окно ввода пароля ПЕРЕД основным UI
        self.show_access_dialog()
    
    def show_access_dialog(self):
        """Окно ввода пароля для доступа к QR и функциям"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Nexus Remote - Access Required")
        dialog.geometry("400x300")
        dialog.configure(bg=self.bg)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрируем
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 400) // 2
        y = (dialog.winfo_screenheight() - 300) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Содержимое
        tk.Label(dialog, text="🔐 Access Required", font=('Segoe UI', 16, 'bold'),
                fg=self.accent, bg=self.bg).pack(pady=(30, 10))
        
        tk.Label(dialog, text="Enter device password to access QR code\nand connection features",
                font=('Segoe UI', 10), fg=self.gray, bg=self.bg, justify=tk.CENTER).pack(pady=(0, 20))
        
        # Информация об устройстве
        info_frame = tk.Frame(dialog, bg=self.card, bd=0, highlightthickness=1, highlightbackground='#2a2a4a')
        info_frame.pack(fill=tk.X, padx=30, pady=(0, 10))
        
        for label, value in [("Device ID", self.client.device_id), ("Default code", self.client.access_code)]:
            row = tk.Frame(info_frame, bg=self.card)
            row.pack(fill=tk.X, padx=15, pady=5)
            tk.Label(row, text=f"{label}:", font=('Segoe UI', 9), fg=self.gray, bg=self.card).pack(side=tk.LEFT)
            tk.Label(row, text=value, font=('Segoe UI', 9, 'bold'), fg=self.text, bg=self.card).pack(side=tk.RIGHT)
        
        # Поле ввода пароля
        pass_frame = tk.Frame(dialog, bg=self.bg)
        pass_frame.pack(fill=tk.X, padx=30, pady=(15, 10))
        
        pass_entry = tk.Entry(pass_frame, font=('Segoe UI', 14, 'bold'), bg='#0f0f1a', fg=self.text,
                             insertbackground=self.text, relief=tk.FLAT, bd=1, justify='center',
                             show="●")
        pass_entry.pack(fill=tk.X, ipady=8)
        pass_entry.focus()
        
        error_label = tk.Label(dialog, text="", font=('Segoe UI', 9), fg=self.red, bg=self.bg)
        error_label.pack()
        
        def verify():
            code = pass_entry.get().strip()
            if self.client.verify_access(code):
                dialog.destroy()
                self.setup_ui()
                threading.Thread(target=self.auto_register, daemon=True).start()
            else:
                error_label.config(text="❌ Invalid code. Try again.")
                pass_entry.delete(0, tk.END)
        
        pass_entry.bind('<Return>', lambda e: verify())
        
        tk.Button(dialog, text="Unlock", font=('Segoe UI', 11, 'bold'),
                 bg=self.accent, fg='white', activebackground=self.accent,
                 relief=tk.FLAT, bd=0, padx=30, pady=10,
                 cursor='hand2', command=verify).pack(pady=(10, 0))
        
        self.root.withdraw()  # Скрываем основное окно
    
    def setup_ui(self):
        self.root.deiconify()  # Показываем основное окно
        
        main = tk.Frame(self.root, bg=self.bg)
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Заголовок
        header = tk.Frame(main, bg=self.bg)
        header.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(header, text="⚡ Nexus Remote", font=('Segoe UI', 22, 'bold'),
                fg=self.accent, bg=self.bg).pack(side=tk.LEFT)
        
        # Кнопка QR (доступна только после ввода пароля)
        self.btn(header, "📷 Show QR", self.accent, self.show_qr_code, 120, 30).pack(side=tk.RIGHT, padx=(5, 0))
        self.btn(header, "🔐 Security →", self.accent,
                lambda: os.startfile(WEB_URL) if sys.platform == 'win32' else None,
                130, 30).pack(side=tk.RIGHT)
        
        # Статус
        self.status_label = tk.Label(main, text="Connecting...", font=('Segoe UI', 10),
                                     fg=self.gray, bg=self.bg)
        self.status_label.pack(anchor='w', pady=(0, 5))
        
        # Вкладки
        nb = ttk.Notebook(main)
        nb.pack(fill=tk.BOTH, expand=True)
        
        self.create_connect_tab(nb)
        self.create_devices_tab(nb)
        self.create_stats_tab(nb)
        
        # Нижняя панель
        bar = tk.Frame(main, bg='#121226', height=30)
        bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))
        bar.pack_propagate(False)
        
        self.bar_dot = tk.Label(bar, text="●", font=('Segoe UI', 10), fg=self.gray, bg='#121226')
        self.bar_dot.pack(side=tk.LEFT, padx=(10, 4))
        self.bar_text = tk.Label(bar, text="Ready", font=('Segoe UI', 8), fg=self.gray, bg='#121226')
        self.bar_text.pack(side=tk.LEFT)
        tk.Label(bar, text=f"🔒 Secured", font=('Segoe UI', 8), fg=self.green, bg='#121226').pack(side=tk.RIGHT, padx=10)
    
    def btn(self, parent, text, color, cmd, w=130, h=32):
        return tk.Button(parent, text=text, font=('Segoe UI', 9, 'bold'), bg=color, fg='white',
                        activebackground=color, relief=tk.FLAT, bd=0, padx=10, pady=5,
                        cursor='hand2', command=cmd)
    
    def entry(self, parent, placeholder=""):
        e = tk.Entry(parent, font=('Segoe UI', 10), bg='#0f0f1a', fg=self.text,
                    insertbackground=self.text, relief=tk.FLAT, bd=1)
        if placeholder:
            e.insert(0, placeholder)
            e.bind('<FocusIn>', lambda ev: e.delete(0, tk.END) if e.get() == placeholder else None)
        return e
    
    def card_frame(self, parent):
        return tk.Frame(parent, bg=self.card, bd=0, highlightthickness=1, highlightbackground='#2a2a4a')
    
    def create_connect_tab(self, nb):
        tab = tk.Frame(nb, bg=self.bg)
        nb.add(tab, text="  🔗 Connect  ")
        
        left = tk.Frame(tab, bg=self.bg)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        c2 = self.card_frame(left)
        c2.pack(fill=tk.X)
        
        tk.Label(c2, text="🔗 Connect to Device", font=('Segoe UI', 12, 'bold'),
                fg=self.accent, bg=self.card).pack(anchor='w', padx=12, pady=(10, 5))
        
        conn = tk.Frame(c2, bg=self.card)
        conn.pack(fill=tk.X, padx=12, pady=(0, 8))
        
        self.peer_entry = self.entry(conn, "Enter Peer ID...")
        self.peer_entry.pack(fill=tk.X, pady=(2, 8))
        
        btn_frame = tk.Frame(conn, bg=self.card)
        btn_frame.pack(fill=tk.X)
        self.btn(btn_frame, "🔗 Connect", self.green, self.do_connect, 120).pack(side=tk.LEFT, padx=(0, 5))
        self.btn(btn_frame, "📋 Copy ID", self.gray, lambda: self.root.clipboard_append(self.client.peer_id), 100).pack(side=tk.LEFT)
        
        right = tk.Frame(tab, bg=self.bg)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        
        c3 = self.card_frame(right)
        c3.pack(fill=tk.X)
        
        tk.Label(c3, text="📺 Capture", font=('Segoe UI', 12, 'bold'),
                fg=self.accent, bg=self.card).pack(anchor='w', padx=12, pady=(10, 5))
        
        self.conn_label = tk.Label(c3, text="Not connected", font=('Segoe UI', 9), fg=self.gray, bg=self.card)
        self.conn_label.pack(anchor='w', padx=12, pady=2)
        
        center = tk.Frame(c3, bg=self.card)
        center.pack(pady=15)
        self.cap_btn = self.btn(center, "▶ Start Capture", self.green, self.toggle_capture, 180)
        self.cap_btn.pack()
        
        self.cap_label = tk.Label(c3, text="● Ready", font=('Segoe UI', 9), fg=self.gray, bg=self.card)
        self.cap_label.pack(pady=(8, 10))
    
    def create_devices_tab(self, nb):
        tab = tk.Frame(nb, bg=self.bg)
        nb.add(tab, text="  💾 Devices  ")
        
        c = self.card_frame(tab)
        c.pack(fill=tk.BOTH, expand=True)
        
        hdr = tk.Frame(c, bg=self.card)
        hdr.pack(fill=tk.X, padx=12, pady=(10, 8))
        tk.Label(hdr, text="💾 Saved Devices", font=('Segoe UI', 12, 'bold'),
                fg=self.accent, bg=self.card).pack(side=tk.LEFT)
        self.btn(hdr, "🔄 Refresh", self.accent, self.refresh_devices, 100, 28).pack(side=tk.RIGHT)
        
        self.dev_list = tk.Frame(c, bg=self.card)
        self.dev_list.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        self.refresh_devices()
    
    def create_stats_tab(self, nb):
        tab = tk.Frame(nb, bg=self.bg)
        nb.add(tab, text="  📊 Stats  ")
        
        c = self.card_frame(tab)
        c.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(c, text="📊 Statistics", font=('Segoe UI', 12, 'bold'),
                fg=self.accent, bg=self.card).pack(anchor='w', padx=12, pady=(10, 5))
        
        self.stats_text = scrolledtext.ScrolledText(c, height=20, font=('Consolas', 9),
                                                     bg='#0f0f1a', fg=self.text, relief=tk.FLAT)
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        
        self.btn(c, "Refresh", self.accent, self.refresh_stats, 100, 30).pack(pady=(0, 8))
    
    # ==================== QR CODE (ЗАЩИЩЕН) ====================
    def show_qr_code(self):
        """Показать QR-код (доступен только после ввода пароля)"""
        qr_data = self.client.generate_qr_data()
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        qr_path = "nexus_qr_temp.png"
        img.save(qr_path)
        
        top = tk.Toplevel(self.root)
        top.title("📷 Nexus Remote - QR Code")
        top.geometry("380x500")
        top.configure(bg=self.bg)
        top.resizable(False, False)
        
        tk.Label(top, text="📷 Scan to Connect", font=('Segoe UI', 14, 'bold'),
                fg=self.accent, bg=self.bg).pack(pady=(20, 5))
        
        tk.Label(top, text="🔒 QR protected by password", font=('Segoe UI', 9),
                fg=self.green, bg=self.bg).pack(pady=(0, 15))
        
        photo = tk.PhotoImage(file=qr_path)
        qr_label = tk.Label(top, image=photo, bg='white', bd=0)
        qr_label.pack(pady=5)
        top.image = photo
        
        # Информация
        info_card = tk.Frame(top, bg=self.card, bd=0, highlightthickness=1, highlightbackground='#2a2a4a')
        info_card.pack(fill=tk.X, padx=20, pady=15)
        
        for label, value in [
            ("Device ID", self.client.device_id),
            ("Peer ID", self.client.peer_id[:24] + "..."),
            ("Access Code", "•" * 8 + " (hidden)")
        ]:
            row = tk.Frame(info_card, bg=self.card)
            row.pack(fill=tk.X, padx=15, pady=3)
            tk.Label(row, text=f"{label}:", font=('Segoe UI', 9), fg=self.gray, bg=self.card).pack(side=tk.LEFT)
            tk.Label(row, text=value, font=('Segoe UI', 9, 'bold'), fg=self.text, bg=self.card).pack(side=tk.RIGHT)
        
        tk.Label(top, text="Share this QR with trusted devices only", font=('Segoe UI', 8),
                fg=self.orange, bg=self.bg).pack(pady=(0, 10))
        
        self.btn(top, "Close", self.accent, top.destroy, 100, 30).pack(pady=(0, 15))
    
    # ==================== ФУНКЦИИ ====================
    def auto_register(self):
        time.sleep(1)
        if self.client.register():
            self.status_label.config(text="✅ Connected to server", fg=self.green)
            self.bar_dot.config(fg=self.green)
        else:
            self.status_label.config(text="❌ Server offline", fg=self.red)
    
    def do_connect(self):
        peer = self.peer_entry.get().strip()
        if not peer or peer == "Enter Peer ID...":
            return messagebox.showwarning("Error", "Enter Peer ID")
        ok, msg = self.client.start_stream(peer)
        if ok:
            self.conn_label.config(text=f"Connected: {peer}", fg=self.green)
            self.bar_dot.config(fg=self.green)
            self.bar_text.config(text="Connected")
        else:
            messagebox.showerror("Error", msg)
    
    def toggle_capture(self):
        if not self.client.capturing:
            if not self.client.connected_peer:
                return messagebox.showwarning("Error", "Connect first")
            self.client.capturing = True
            self.cap_btn.config(text="⏹ Stop", bg=self.red)
            self.cap_label.config(text="● Capturing...", fg=self.orange)
            self.bar_dot.config(fg=self.orange)
            threading.Thread(target=self.capture_loop, daemon=True).start()
        else:
            self.client.capturing = False
            self.client.stop_stream()
            self.cap_btn.config(text="▶ Start Capture", bg=self.green)
            self.cap_label.config(text="● Ready", fg=self.gray)
            self.bar_dot.config(fg=self.green)
    
    def capture_loop(self):
        while self.client.capturing:
            try:
                ss = pyautogui.screenshot()
                buf = io.BytesIO()
                ss.save(buf, format='JPEG', quality=50)
                self.client.send_frame(buf.getvalue())
                time.sleep(1/self.client.fps)
            except:
                time.sleep(1)
    
    def refresh_devices(self):
        for w in self.dev_list.winfo_children():
            w.destroy()
        devices = self.client.get_saved_devices()
        if not devices:
            tk.Label(self.dev_list, text="No saved devices", fg=self.gray, bg=self.card).pack(expand=True)
            return
        for dev in devices:
            peer_id, name, platf, last, fav = dev[:5]
            row = tk.Frame(self.dev_list, bg='#1e1e38', bd=0, highlightthickness=1, highlightbackground='#2a2a4a')
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=name or peer_id[:15], font=('Segoe UI', 9, 'bold'),
                    fg=self.text, bg='#1e1e38', width=18, anchor='w').pack(side=tk.LEFT, padx=8, pady=6)
            tk.Label(row, text=last[:16] if last else "Never", font=('Segoe UI', 8), fg=self.gray, bg='#1e1e38', width=16).pack(side=tk.LEFT, padx=4, pady=6)
            btn_f = tk.Frame(row, bg='#1e1e38')
            btn_f.pack(side=tk.RIGHT, padx=8)
            self.btn(btn_f, "▶", self.green, lambda p=peer_id: self.quick_connect(p), 28, 24).pack(side=tk.LEFT, padx=1)
            self.btn(btn_f, "✏️", self.accent, lambda p=peer_id, n=name: self.rename_dev(p, n or p), 28, 24).pack(side=tk.LEFT, padx=1)
            self.btn(btn_f, "✕", self.red, lambda p=peer_id: self.remove_dev(p), 28, 24).pack(side=tk.LEFT, padx=1)
    
    def quick_connect(self, peer_id):
        ok, msg = self.client.start_stream(peer_id)
        if ok:
            self.conn_label.config(text=f"Connected: {peer_id}", fg=self.green)
        else:
            messagebox.showerror("Error", msg)
    
    def rename_dev(self, peer_id, old_name):
        new_name = simpledialog.askstring("Rename", "New name:", initialvalue=old_name)
        if new_name:
            self.client.update_device_name(peer_id, new_name)
            self.refresh_devices()
    
    def remove_dev(self, peer_id):
        if messagebox.askyesno("Remove", f"Remove {peer_id}?"):
            self.client.db.execute('DELETE FROM devices WHERE peer_id=?', (peer_id,))
            self.client.db.commit()
            self.refresh_devices()
    
    def refresh_stats(self):
        self.stats_text.delete('1.0', tk.END)
        stats = self.client.get_stats()
        if not stats:
            self.stats_text.insert('1.0', "No statistics yet")
            return
        for row in stats:
            self.stats_text.insert(tk.END, f"Peer: {row[0]}\n  Frames: {row[1]} | Data: {(row[2] or 0)//1024}KB | Duration: {row[3]}s | FPS: {row[4]:.1f}\n\n")
    
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()
    
    def on_close(self):
        self.client.capturing = False
        self.client.stop_stream()
        self.root.destroy()

if __name__ == "__main__":
    app = NexusUI()
    app.run()
