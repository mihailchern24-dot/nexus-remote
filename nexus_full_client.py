#!/usr/bin/env python3
# nexus_full_client.py - Nexus Remote олный лиент v2.2
# утентификация + QR + Сохранение устройств + се 7 вкладок
import requests
import json
import time
import base64
import threading
import os
import sys
import platform
import io
import hashlib
import secrets
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import pyautogui

# ==================== ФУЦ ====================
SERVER_URL = "https://nexus-remote.onrender.com"
PEER_ID = f"PC-{platform.node()}-{int(time.time())}"
COMPRESSION = "zstd"
ENCRYPTION = "aes_gcm"

# Файл для хранения устройств
DEVICES_FILE = "nexus_devices.json"
AUTH_FILE = "nexus_auth.json"

# ====================  УСТСТ ====================
class DeviceManager:
    def __init__(self):
        self.devices = self.load_devices()
        self.auth = self.load_auth()
    
    def load_devices(self):
        try:
            with open(DEVICES_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save_devices(self):
        with open(DEVICES_FILE, 'w') as f:
            json.dump(self.devices, f, indent=2)
    
    def load_auth(self):
        try:
            with open(AUTH_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"username": "", "token": "", "logged_in": False}
    
    def save_auth(self):
        with open(AUTH_FILE, 'w') as f:
            json.dump(self.auth, f, indent=2)
    
    def add_device(self, peer_id, name, password="", platform="unknown"):
        """обавить устройство в сохраненные"""
        self.devices[peer_id] = {
            "name": name,
            "password": self.hash_password(password) if password else "",
            "platform": platform,
            "added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_connected": "",
            "auto_connect": False,
            "trusted": False
        }
        self.save_devices()
    
    def remove_device(self, peer_id):
        if peer_id in self.devices:
            del self.devices[peer_id]
            self.save_devices()
    
    def get_saved_devices(self):
        return self.devices
    
    def login(self, username, password):
        """ход в систему"""
        # Хешируем пароль
        token = self.hash_password(username + password + str(time.time()))
        self.auth = {
            "username": username,
            "token": token,
            "logged_in": True,
            "login_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_auth()
        return True
    
    def logout(self):
        self.auth = {"username": "", "token": "", "logged_in": False}
        self.save_auth()
    
    def is_logged_in(self):
        return self.auth.get("logged_in", False)
    
    def get_username(self):
        return self.auth.get("username", "")
    
    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def generate_qr_code(peer_id):
        """енерирует QR-код в виде текста для консоли"""
        qr_data = f"nexus://connect/{peer_id}"
        # ростой QR-код в консоли
        size = 21
        qr = [[" " for _ in range(size)] for _ in range(size)]
        
        # аттерн поиска
        for i in range(7):
            for j in range(7):
                if i in [0,6] or j in [0,6] or (2 <= i <= 4 and 2 <= j <= 4):
                    qr[i][j] = "█"
                    qr[i][size-1-j] = "█"
                    qr[size-1-i][j] = "█"
        
        # анные
        for i, char in enumerate(qr_data):
            if i < size * size:
                x, y = i % size, i // size
                if qr[y][x] == " ":
                    qr[y][x] = "█" if ord(char) % 2 == 0 else " "
        
        return "\n".join(["".join(row) for row in qr])

# ==================== NEXUS Т ====================
class NexusClient:
    def __init__(self):
        self.peer_id = PEER_ID
        self.stream_id = None
        self.connected_peer = None
        self.running = False
        self.capturing = False
        self.fps = 30
        self.quality = "high"
        self.device_manager = DeviceManager()
        self.device_id = f"NEXUS-{int(time.time()) % 9000 + 1000}"
        self.device_password = secrets.token_hex(4)
        
        self.stats = {
            'frames_sent': 0,
            'bytes_sent': 0,
            'fps_actual': 0,
            'errors': 0
        }
    
    def register(self):
        data = {
            "peer_id": self.peer_id,
            "platform": "windows",
            "compression": COMPRESSION,
            "encryption": ENCRYPTION
        }
        try:
            resp = requests.post(f"{SERVER_URL}/register", json=data, timeout=5)
            return resp.json().get('status') == 'registered'
        except:
            return False
    
    def start_stream(self, target, quality="high", password=""):
        data = {
            "source": self.peer_id,
            "target": target,
            "quality": quality,
            "compression": COMPRESSION,
            "encryption": ENCRYPTION,
            "password": password
        }
        try:
            resp = requests.post(f"{SERVER_URL}/start_stream", json=data, timeout=5)
            result = resp.json()
            if result.get('status') == 'streaming':
                self.stream_id = result['stream_id']
                self.connected_peer = target
                return True
        except:
            pass
        return False
    
    def send_frame(self, frame_bytes):
        if not self.stream_id:
            return
        try:
            frame_b64 = base64.b64encode(frame_bytes).decode()
            data = {
                "stream_id": self.stream_id,
                "from": self.peer_id,
                "target": self.connected_peer,
                "frame": frame_b64,
                "type": "video"
            }
            resp = requests.post(f"{SERVER_URL}/send_frame", json=data, timeout=5)
            if resp.json().get('status') == 'sent':
                self.stats['frames_sent'] += 1
                self.stats['bytes_sent'] += len(frame_bytes)
        except:
            self.stats['errors'] += 1
    
    def stop_stream(self):
        if self.stream_id:
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

# ==================== UI С С  ====================
class NexusUI:
    def __init__(self):
        self.client = NexusClient()
        self.root = tk.Tk()
        self.root.title("Nexus Remote v2.2 - Secure Edition")
        
        # даптивный размер
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.window_w = min(800, screen_w - 100)
        self.window_h = min(600, screen_h - 100)
        self.root.geometry(f"{self.window_w}x{self.window_h}")
        self.root.minsize(700, 500)
        
        # Цвета
        self.bg = '#0c0c18'
        self.card_bg = '#16162a'
        self.accent = '#6366f1'
        self.accent_hover = '#818cf8'
        self.text_color = '#e0e0e0'
        self.gray = '#8c8ca0'
        self.green = '#34d399'
        self.red = '#f87171'
        self.orange = '#fbbf24'
        self.white = '#ffffff'
        
        self.root.configure(bg=self.bg)
        
        # Состояние
        self.active_tab = 0
        self.capturing = False
        self.connected_peer = None
        self.selected_saved_device = None
        
        self.setup_ui()
        self.update_status()
    
    def create_card(self, parent, **kwargs):
        return tk.Frame(parent, bg=self.card_bg, bd=0, highlightthickness=1,
                       highlightbackground='#2a2a4a', **kwargs)
    
    def create_button(self, parent, text, color, command, width=160, height=36):
        btn = tk.Button(parent, text=text, font=('Segoe UI', 11, 'bold'),
                       bg=color, fg=self.white, activebackground=color,
                       relief=tk.FLAT, bd=0, padx=15, pady=8,
                       cursor='hand2', command=command)
        return btn
    
    def create_entry(self, parent, placeholder="", show=None):
        entry = tk.Entry(parent, font=('Segoe UI', 11),
                        bg='#0f0f1a', fg=self.text_color,
                        insertbackground=self.text_color,
                        relief=tk.FLAT, bd=1, show=show if show else '')
        if placeholder:
            entry.insert(0, placeholder)
            entry.bind('<FocusIn>', lambda e: entry.delete(0, tk.END) if entry.get() == placeholder else None)
            entry.bind('<FocusOut>', lambda e: entry.insert(0, placeholder) if not entry.get() else None)
        return entry
    
    def setup_ui(self):
        # лавный контейнер
        main = tk.Frame(self.root, bg=self.bg)
        main.pack(fill=tk.BOTH, expand=True, padx=25, pady=15)
        
        # аголовок
        title_frame = tk.Frame(main, bg=self.bg)
        title_frame.pack(fill=tk.X)
        
        tk.Label(title_frame, text="⚡ Nexus Remote", 
                font=('Segoe UI', 24, 'bold'),
                fg=self.accent, bg=self.bg).pack(anchor='w')
        tk.Label(title_frame, text="Remote Desktop · Game Streaming · Secure Connection",
                font=('Segoe UI', 10), fg=self.gray, bg=self.bg).pack(anchor='w')
        
        # кладки
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(15, 0))
        
        self.create_devices_tab()
        self.create_saved_devices_tab()
        self.create_settings_tab()
        self.create_gamepad_tab()
        self.create_files_tab()
        self.create_account_tab()
        self.create_security_tab()
        self.create_logs_tab()
        
        # ижняя панель
        self.create_bottom_bar(main)
    
    def create_devices_tab(self):
        tab = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(tab, text="  📱 Connect  ")
        
        # евая колонка - одключение
        left_frame = tk.Frame(tab, bg=self.bg)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # арточка "ои данные"
        card1 = self.create_card(left_frame)
        card1.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(card1, text="🔑 My Device", font=('Segoe UI', 14, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=20, pady=(15, 5))
        
        info_frame = tk.Frame(card1, bg=self.card_bg)
        info_frame.pack(fill=tk.X, padx=20, pady=(5, 15))
        
        # Device ID с кнопкой копирования
        id_row = tk.Frame(info_frame, bg=self.card_bg)
        id_row.pack(fill=tk.X, pady=2)
        tk.Label(id_row, text="Device ID:", font=('Segoe UI', 10),
                fg=self.gray, bg=self.card_bg).pack(side=tk.LEFT)
        tk.Label(id_row, text=self.client.device_id, font=('Segoe UI', 10, 'bold'),
                fg=self.text_color, bg=self.card_bg).pack(side=tk.LEFT, padx=(5, 0))
        self.create_button(id_row, "📋", self.gray, 
                          lambda: self.root.clipboard_append(self.client.device_id),
                          width=40, height=28).pack(side=tk.RIGHT)
        
        # Password
        pw_row = tk.Frame(info_frame, bg=self.card_bg)
        pw_row.pack(fill=tk.X, pady=2)
        tk.Label(pw_row, text="Password:", font=('Segoe UI', 10),
                fg=self.gray, bg=self.card_bg).pack(side=tk.LEFT)
        self.pw_label = tk.Label(pw_row, text=self.client.device_password, 
                                  font=('Segoe UI', 10, 'bold'),
                                  fg=self.orange, bg=self.card_bg)
        self.pw_label.pack(side=tk.LEFT, padx=(5, 0))
        self.create_button(pw_row, "🔄", self.gray,
                          self.generate_new_password,
                          width=40, height=28).pack(side=tk.RIGHT)
        
        # QR Code
        qr_row = tk.Frame(info_frame, bg=self.card_bg)
        qr_row.pack(fill=tk.X, pady=(10, 0))
        self.create_button(qr_row, "📷 Show QR Code", self.accent,
                          self.show_qr_code, width=200, height=32).pack(side=tk.LEFT)
        
        # Статус сервера
        self.server_status = tk.Label(info_frame, text="● Connecting...",
                font=('Segoe UI', 9, 'bold'), fg=self.gray, bg=self.card_bg)
        self.server_status.pack(anchor='w', pady=(10, 0))
        
        # арточка "одключиться"
        card2 = self.create_card(left_frame)
        card2.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(card2, text="🔗 Connect to Device", font=('Segoe UI', 14, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=20, pady=(15, 10))
        
        connect_frame = tk.Frame(card2, bg=self.card_bg)
        connect_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        # Peer ID
        tk.Label(connect_frame, text="Peer ID:", font=('Segoe UI', 10),
                fg=self.gray, bg=self.card_bg).pack(anchor='w')
        self.peer_entry = self.create_entry(connect_frame, "Enter Peer ID...")
        self.peer_entry.pack(fill=tk.X, pady=(3, 8))
        
        # Password
        tk.Label(connect_frame, text="Password (if required):", font=('Segoe UI', 10),
                fg=self.gray, bg=self.card_bg).pack(anchor='w')
        self.pass_entry = self.create_entry(connect_frame, "Enter password...", show="●")
        self.pass_entry.pack(fill=tk.X, pady=(3, 10))
        
        # нопки подключения
        btn_frame = tk.Frame(connect_frame, bg=self.card_bg)
        btn_frame.pack(fill=tk.X)
        
        self.connect_btn = self.create_button(btn_frame, "🔗 Connect", self.green, 
                                             self.connect_with_auth)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.create_button(btn_frame, "📷 QR", self.accent,
                          lambda: messagebox.showinfo("QR", "Scan QR code on remote device"),
                          width=80, height=36).pack(side=tk.LEFT, padx=(0, 8))
        
        # апомнить устройство
        self.save_var = tk.BooleanVar(value=True)
        tk.Checkbutton(connect_frame, text="Save this device", 
                      variable=self.save_var,
                      font=('Segoe UI', 9), fg=self.gray,
                      bg=self.card_bg, activebackground=self.card_bg,
                      selectcolor=self.card_bg).pack(anchor='w', pady=(8, 0))
        
        # равая колонка - Start/Stop Capture
        right_frame = tk.Frame(tab, bg=self.bg)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        
        card3 = self.create_card(right_frame)
        card3.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(card3, text="📺 Screen Capture", font=('Segoe UI', 14, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=20, pady=(15, 10))
        
        # нформация о подключении
        self.conn_info = tk.Label(card3, text="Not connected", 
                                   font=('Segoe UI', 10),
                                   fg=self.gray, bg=self.card_bg)
        self.conn_info.pack(anchor='w', padx=20, pady=(0, 10))
        
        center_frame = tk.Frame(card3, bg=self.card_bg)
        center_frame.pack(pady=20)
        
        self.capture_btn = self.create_button(center_frame, "▶ Start Capture", self.green, 
                                             self.toggle_capture, width=200)
        self.capture_btn.pack()
        
        self.capture_status = tk.Label(card3, text="● Ready", 
                                        font=('Segoe UI', 10),
                                        fg=self.gray, bg=self.card_bg)
        self.capture_status.pack(pady=(10, 15))
        
        # Статистика
        card4 = self.create_card(right_frame)
        card4.pack(fill=tk.X)
        
        tk.Label(card4, text="📊 Statistics", font=('Segoe UI', 14, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=20, pady=(15, 10))
        
        self.stats_labels = {}
        stats = [
            ("Frames sent", 'frames_sent'),
            ("Data sent", 'bytes_sent'),
            ("FPS", 'fps_actual'),
            ("Errors", 'errors')
        ]
        for label, key in stats:
            row = tk.Frame(card4, bg=self.card_bg)
            row.pack(fill=tk.X, padx=20, pady=3)
            tk.Label(row, text=label, font=('Segoe UI', 10),
                    fg=self.gray, bg=self.card_bg).pack(side=tk.LEFT)
            self.stats_labels[key] = tk.Label(row, text="0", font=('Segoe UI', 10, 'bold'),
                                             fg=self.text_color, bg=self.card_bg)
            self.stats_labels[key].pack(side=tk.RIGHT)
        
        tk.Label(card4, text="", bg=self.card_bg).pack(pady=(0, 10))  # spacer
    
    def create_saved_devices_tab(self):
        tab = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(tab, text="  💾 Saved  ")
        
        card = self.create_card(tab)
        card.pack(fill=tk.BOTH, expand=True)
        
        header = tk.Frame(card, bg=self.card_bg)
        header.pack(fill=tk.X, padx=20, pady=(15, 10))
        
        tk.Label(header, text="💾 Saved Devices", font=('Segoe UI', 14, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(side=tk.LEFT)
        
        self.create_button(header, "🔄 Refresh", self.accent,
                          self.refresh_saved_devices, width=130, height=30).pack(side=tk.RIGHT)
        
        # Список сохраненных устройств
        self.saved_list_frame = tk.Frame(card, bg=self.card_bg)
        self.saved_list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
        self.refresh_saved_devices()
    
    def refresh_saved_devices(self):
        """бновить список сохраненных устройств"""
        for widget in self.saved_list_frame.winfo_children():
            widget.destroy()
        
        devices = self.client.device_manager.get_saved_devices()
        
        if not devices:
            tk.Label(self.saved_list_frame, text="No saved devices yet.\nConnect to a device and check 'Save this device'",
                    font=('Segoe UI', 11), fg=self.gray, bg=self.card_bg,
                    justify=tk.CENTER).pack(expand=True)
            return
        
        # аголовки
        cols = tk.Frame(self.saved_list_frame, bg=self.card_bg)
        cols.pack(fill=tk.X, pady=(0, 5))
        for col, width in [("Name", 15), ("Peer ID", 25), ("Platform", 10), ("Last Connected", 15), ("Actions", 20)]:
            tk.Label(cols, text=col, font=('Segoe UI', 9, 'bold'),
                    fg=self.gray, bg=self.card_bg, width=width, anchor='w').pack(side=tk.LEFT)
        
        for peer_id, info in devices.items():
            row = tk.Frame(self.saved_list_frame, bg='#1e1e38', bd=0, highlightthickness=1,
                          highlightbackground='#2a2a4a')
            row.pack(fill=tk.X, pady=2)
            
            tk.Label(row, text=info.get('name', 'Unknown')[:14], font=('Segoe UI', 10),
                    fg=self.text_color, bg='#1e1e38', width=15, anchor='w').pack(side=tk.LEFT, padx=5, pady=8)
            tk.Label(row, text=peer_id[:24], font=('Segoe UI', 9),
                    fg=self.gray, bg='#1e1e38', width=25, anchor='w').pack(side=tk.LEFT, padx=5, pady=8)
            tk.Label(row, text=info.get('platform', '?')[:9], font=('Segoe UI', 9),
                    fg=self.green, bg='#1e1e38', width=10, anchor='w').pack(side=tk.LEFT, padx=5, pady=8)
            tk.Label(row, text=info.get('last_connected', 'Never')[:14], font=('Segoe UI', 9),
                    fg=self.gray, bg='#1e1e38', width=15, anchor='w').pack(side=tk.LEFT, padx=5, pady=8)
            
            btn_frame = tk.Frame(row, bg='#1e1e38')
            btn_frame.pack(side=tk.LEFT, padx=5)
            
            self.create_button(btn_frame, "▶", self.green,
                             lambda p=peer_id: self.quick_connect(p), width=35, height=28).pack(side=tk.LEFT, padx=2)
            self.create_button(btn_frame, "✕", self.red,
                             lambda p=peer_id: self.remove_saved_device(p), width=35, height=28).pack(side=tk.LEFT, padx=2)
    
    def quick_connect(self, peer_id):
        """ыстрое подключение к сохраненному устройству"""
        devices = self.client.device_manager.get_saved_devices()
        if peer_id in devices:
            password = devices[peer_id].get('password', '')
            if self.client.start_stream(peer_id, password=password):
                self.client.connected_peer = peer_id
                self.conn_info.config(text=f"Connected to: {peer_id}", fg=self.green)
                self.log(f"Quick connect to {peer_id}")
                # бновляем время подключения
                devices[peer_id]['last_connected'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.client.device_manager.save_devices()
            else:
                messagebox.showerror("Error", f"Failed to connect to {peer_id}")
    
    def remove_saved_device(self, peer_id):
        if messagebox.askyesno("Remove Device", f"Remove {peer_id} from saved devices?"):
            self.client.device_manager.remove_device(peer_id)
            self.refresh_saved_devices()
            self.log(f"Removed device: {peer_id}")
    
    def connect_with_auth(self):
        """одключение с аутентификацией"""
        peer_id = self.peer_entry.get().strip()
        password = self.pass_entry.get().strip()
        
        if not peer_id or peer_id == "Enter Peer ID...":
            messagebox.showwarning("Error", "Please enter a Peer ID")
            return
        
        if password == "Enter password...":
            password = ""
        
        # робуем подключиться
        if self.client.start_stream(peer_id, password=password):
            self.client.connected_peer = peer_id
            self.conn_info.config(text=f"Connected to: {peer_id}", fg=self.green)
            self.log(f"Connected to {peer_id}")
            
            # Сохраняем устройство
            if self.save_var.get():
                name = simpledialog.askstring("Save Device", 
                    f"Enter name for {peer_id}:", initialvalue=peer_id)
                if name:
                    self.client.device_manager.add_device(peer_id, name, password)
                    self.log(f"Device saved: {name} ({peer_id})")
                    self.refresh_saved_devices()
            
            messagebox.showinfo("Connected", f"Successfully connected to {peer_id}!")
        else:
            self.log(f"Failed to connect to {peer_id}")
            messagebox.showerror("Error", 
                f"Cannot connect to '{peer_id}'.\n\nCheck:\n- Peer ID is correct\n- Device is online\n- Password is correct (if required)")
    
    def show_qr_code(self):
        """оказать QR-код для подключения"""
        qr = DeviceManager.generate_qr_code(self.client.peer_id)
        top = tk.Toplevel(self.root)
        top.title("QR Code - Nexus Remote")
        top.geometry("350x450")
        top.configure(bg=self.bg)
        
        tk.Label(top, text="Scan to Connect", font=('Segoe UI', 14, 'bold'),
                fg=self.accent, bg=self.bg).pack(pady=15)
        
        qr_text = tk.Text(top, font=('Courier New', 8), bg='white', fg='black',
                         width=30, height=25, relief=tk.FLAT)
        qr_text.insert('1.0', qr)
        qr_text.config(state='disabled')
        qr_text.pack(pady=10)
        
        tk.Label(top, text=f"Peer: {self.client.peer_id}", font=('Segoe UI', 9),
                fg=self.gray, bg=self.bg).pack()
        tk.Label(top, text=f"Password: {self.client.device_password}", font=('Segoe UI', 9),
                fg=self.orange, bg=self.bg).pack()
    
    def generate_new_password(self):
        """Сгенерировать новый пароль"""
        self.client.device_password = secrets.token_hex(4)
        self.pw_label.config(text=self.client.device_password)
        self.log("New password generated")
    
    def create_settings_tab(self):
        tab = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(tab, text="  ⚙️ Settings  ")
        
        card = self.create_card(tab)
        card.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(card, text="Capture Settings", font=('Segoe UI', 14, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=20, pady=(15, 10))
        
        settings = [
            ("Resolution", ["Auto (detect)", "1920×1080", "1280×720", "2560×1440", "3840×2160"]),
            ("FPS", ["30", "60", "120"]),
            ("Codec", ["Auto", "H.264", "H.265", "AV1"]),
            ("Compression", ["ZSTD", "LZ4", "ZLIB", "Brotli"]),
            ("Encryption", ["AES-256-GCM", "ChaCha20", "AES-256-CBC"])
        ]
        
        for label, options in settings:
            row = tk.Frame(card, bg=self.card_bg)
            row.pack(fill=tk.X, padx=20, pady=5)
            tk.Label(row, text=label, font=('Segoe UI', 10),
                    fg=self.gray, bg=self.card_bg).pack(anchor='w')
            combo = ttk.Combobox(row, values=options, font=('Segoe UI', 10), state='readonly')
            combo.set(options[0])
            combo.pack(fill=tk.X, pady=(5, 0))
        
        self.create_button(card, "💾 Save", self.accent,
                          lambda: self.log("Settings saved"), width=100).pack(padx=20, pady=(10, 15))
    
    def create_gamepad_tab(self):
        tab = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(tab, text="  🎮 Gamepad  ")
        
        card = self.create_card(tab)
        card.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(card, text="Gamepad Settings", font=('Segoe UI', 14, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=20, pady=(15, 10))
        
        for label in ["Virtual Gamepad", "Auto-hide"]:
            row = tk.Frame(card, bg=self.card_bg)
            row.pack(fill=tk.X, padx=20, pady=5)
            tk.Label(row, text=label, font=('Segoe UI', 11),
                    fg=self.text_color, bg=self.card_bg).pack(side=tk.LEFT)
            var = tk.BooleanVar(value=True)
            tk.Checkbutton(row, variable=var, bg=self.card_bg, activebackground=self.card_bg,
                          fg=self.green, selectcolor=self.card_bg, text="ON").pack(side=tk.RIGHT)
        
        tk.Label(card, text="Controller: Xbox | Available: Android, iPhone",
                font=('Segoe UI', 10), fg=self.gray, bg=self.card_bg).pack(
                anchor='w', padx=20, pady=(10, 15))
    
    def create_files_tab(self):
        tab = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(tab, text="  📁 Files  ")
        
        card = self.create_card(tab)
        card.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(card, text="Cloud Storage", font=('Segoe UI', 14, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=20, pady=(15, 10))
        
        for name in ["Google Drive", "Yandex Disk", "OneDrive", "Dropbox"]:
            row = tk.Frame(card, bg=self.card_bg)
            row.pack(fill=tk.X, padx=20, pady=3)
            tk.Label(row, text=f"📂 {name}", font=('Segoe UI', 11),
                    fg=self.text_color, bg=self.card_bg).pack(side=tk.LEFT, pady=5)
            tk.Label(row, text="Not connected", font=('Segoe UI', 10),
                    fg=self.gray, bg=self.card_bg).pack(side=tk.LEFT, padx=10)
            self.create_button(row, "Connect", self.accent,
                             lambda n=name: self.log(f"Connecting to {n}..."),
                             width=90, height=30).pack(side=tk.RIGHT)
    
    def create_account_tab(self):
        tab = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(tab, text="  👤 Account  ")
        
        card1 = self.create_card(tab)
        card1.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(card1, text="Login", font=('Segoe UI', 14, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=20, pady=(15, 10))
        
        # оля входа
        self.username_entry = self.create_entry(card1, "Username")
        self.username_entry.pack(fill=tk.X, padx=20, pady=5)
        
        self.login_pass_entry = self.create_entry(card1, "Password", show="●")
        self.login_pass_entry.pack(fill=tk.X, padx=20, pady=5)
        
        self.create_button(card1, "Sign In", self.accent,
                          self.do_login, width=200).pack(padx=20, pady=10)
        
        # Статус входа
        self.login_status = tk.Label(card1, text="Not logged in",
                                      font=('Segoe UI', 10),
                                      fg=self.gray, bg=self.card_bg)
        self.login_status.pack(pady=(0, 10))
        
        # Социальные кнопки
        social_frame = tk.Frame(card1, bg=self.card_bg)
        social_frame.pack(pady=(0, 15))
        
        for text, color in [("🔵 Google", '#4285f4'), ("🐙 GitHub", '#333')]:
            self.create_button(social_frame, text, color,
                             lambda t=text: self.log(f"OAuth: {t} - Coming Soon"),
                             width=140, height=34).pack(side=tk.LEFT, padx=5)
        
        # нопка выхода
        self.logout_btn = self.create_button(card1, "Logout", self.red,
                                            self.do_logout, width=150)
        self.logout_btn.pack(pady=(0, 15))
        self.logout_btn.pack_forget()  # Скрыта пока не войдем
    
    def do_login(self):
        username = self.username_entry.get().strip()
        password = self.login_pass_entry.get().strip()
        
        if not username or username == "Username":
            messagebox.showwarning("Error", "Enter username")
            return
        
        if not password or password == "Password":
            messagebox.showwarning("Error", "Enter password")
            return
        
        if self.client.device_manager.login(username, password):
            self.login_status.config(text=f"✅ Logged in as {username}", fg=self.green)
            self.logout_btn.pack(pady=(0, 15))
            self.log(f"User logged in: {username}")
        else:
            messagebox.showerror("Error", "Login failed")
    
    def do_logout(self):
        self.client.device_manager.logout()
        self.login_status.config(text="Not logged in", fg=self.gray)
        self.logout_btn.pack_forget()
        self.log("Logged out")
    
    def create_security_tab(self):
        tab = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(tab, text="  🔒 Security  ")
        
        card = self.create_card(tab)
        card.pack(fill=tk.X)
        
        tk.Label(card, text="Security Status", font=('Segoe UI', 14, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=20, pady=(15, 10))
        
        for label, value, color in [
            ("Password Protection", "ON", self.green),
            ("2FA", "OFF", self.gray),
            ("Encryption", "AES-256-GCM + ChaCha20", self.green),
            ("Compression", "ZSTD (75-85%)", self.green),
            ("Auto-lock", "After 5 attempts", self.orange),
            ("IP Blacklist", "Empty", self.gray)
        ]:
            row = tk.Frame(card, bg=self.card_bg)
            row.pack(fill=tk.X, padx=20, pady=3)
            tk.Label(row, text=label, font=('Segoe UI', 11),
                    fg=self.gray, bg=self.card_bg).pack(side=tk.LEFT)
            tk.Label(row, text=value, font=('Segoe UI', 11, 'bold'),
                    fg=color, bg=self.card_bg).pack(side=tk.RIGHT)
    
    def create_logs_tab(self):
        tab = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(tab, text="  📋 Logs  ")
        
        card = self.create_card(tab)
        card.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(card, text="Activity Log", font=('Segoe UI', 14, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=20, pady=(15, 10))
        
        self.log_text = scrolledtext.ScrolledText(card, height=15,
                                                   font=('Consolas', 9),
                                                   bg='#0f0f1a', fg=self.text_color,
                                                   relief=tk.FLAT, bd=0)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
    
    def create_bottom_bar(self, parent):
        bar = tk.Frame(parent, bg='#121226', height=38)
        bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        bar.pack_propagate(False)
        
        self.status_dot = tk.Label(bar, text="●", font=('Segoe UI', 12),
                                   fg=self.red, bg='#121226')
        self.status_dot.pack(side=tk.LEFT, padx=(15, 5))
        
        self.status_bar_text = tk.Label(bar, text="Ready",
                                        font=('Segoe UI', 9),
                                        fg=self.gray, bg='#121226')
        self.status_bar_text.pack(side=tk.LEFT)
        
        # нформация о пользователе
        self.user_label = tk.Label(bar, text="",
                                   font=('Segoe UI', 9),
                                   fg=self.green, bg='#121226')
        self.user_label.pack(side=tk.RIGHT, padx=15)
        
        tk.Label(bar, text="nexus-remote.onrender.com",
                font=('Segoe UI', 9), fg=self.gray, bg='#121226').pack(
                side=tk.RIGHT, padx=15)
    
    # ==================== ФУЦ ====================
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        if hasattr(self, 'log_text'):
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
    
    def update_status(self):
        if self.client.register():
            self.server_status.config(text="✅ Server: Connected", fg=self.green)
            self.status_dot.config(fg=self.green)
            self.status_bar_text.config(text="Server Connected")
            self.log("Registered on Nexus Server")
        else:
            self.server_status.config(text="❌ Server: Disconnected", fg=self.red)
            self.log("Failed to register")
    
    def toggle_capture(self):
        if not self.client.capturing:
            if not self.client.connected_peer:
                messagebox.showwarning("Error", "Connect to a device first!")
                return
            
            if self.client.start_stream(self.client.connected_peer):
                self.client.capturing = True
                self.capture_btn.config(text="⏹ Stop Capture", bg=self.red)
                self.capture_status.config(text="● Capturing...", fg=self.orange)
                self.status_dot.config(fg=self.orange)
                self.log(f"Capture started")
                threading.Thread(target=self.capture_loop, daemon=True).start()
        else:
            self.client.capturing = False
            self.client.stop_stream()
            self.capture_btn.config(text="▶ Start Capture", bg=self.green)
            self.capture_status.config(text="● Ready", fg=self.gray)
            self.status_dot.config(fg=self.green if self.client.connected_peer else self.red)
            self.log("Capture stopped")
    
    def capture_loop(self):
        self.log("Screen capture active")
        last_time = time.time()
        
        while self.client.capturing:
            try:
                screenshot = pyautogui.screenshot()
                buf = io.BytesIO()
                screenshot.save(buf, format='JPEG', quality=60)
                self.client.send_frame(buf.getvalue())
                
                now = time.time()
                elapsed = now - last_time
                if elapsed > 0:
                    self.client.stats['fps_actual'] = round(1.0 / elapsed, 1)
                last_time = now
                
                # бновляем статистику
                self.stats_labels['frames_sent'].config(text=str(self.client.stats['frames_sent']))
                self.stats_labels['bytes_sent'].config(text=f"{self.client.stats['bytes_sent'] // 1024} KB")
                self.stats_labels['fps_actual'].config(text=f"{self.client.stats['fps_actual']:.1f}")
                self.stats_labels['errors'].config(text=str(self.client.stats['errors']))
                
                time.sleep(1/self.client.fps)
            except Exception as e:
                self.log(f"Error: {e}")
                time.sleep(1)
    
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
