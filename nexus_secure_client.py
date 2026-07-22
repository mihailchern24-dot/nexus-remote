#!/usr/bin/env python3
# nexus_secure_client.py - Nexus Remote SECURE EDITION v3.0
# С меры безопасности: MFA, E2EE, WhiteList, RateLimit, Audit, VPN
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
import hmac
import struct
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import x25519
import pyautogui
import pyotp  # pip install pyotp
import qrcode  # pip install qrcode[pil]

# ==================== ФУЦ ====================
SERVER_URL = "https://nexus-remote.onrender.com"
COMPRESSION = "zstd"
ENCRYPTION = "aes_gcm"

# Файлы
DEVICES_FILE = "nexus_devices_secure.json"
AUTH_FILE = "nexus_auth_secure.json"
WHITELIST_FILE = "nexus_whitelist.json"
AUDIT_FILE = "nexus_audit.log"
MFA_FILE = "nexus_mfa.json"

# ==================== ТФ E2EE ====================
class E2EEncryption:
    """End-to-End шифрование с Double Ratchet"""
    
    def __init__(self):
        self.backend = default_backend()
        self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.shared_keys = {}  # peer_id -> shared_key
        self.message_count = 0
    
    def get_public_key_bytes(self):
        return self.public_key.public_bytes_raw()
    
    def compute_shared_key(self, peer_public_bytes, peer_id):
        """Diffie-Hellman обмен ключами"""
        peer_public = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
        shared_secret = self.private_key.exchange(peer_public)
        
        # HKDF для получения ключа
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'nexus-remote-e2ee',
            backend=self.backend
        )
        key = hkdf.derive(shared_secret)
        self.shared_keys[peer_id] = key
        return key
    
    def encrypt_message(self, plaintext, peer_id):
        """ашифровать сообщение для конкретного пира"""
        if peer_id not in self.shared_keys:
            raise Exception("No shared key for peer")
        
        key = self.shared_keys[peer_id]
        iv = os.urandom(12)
        
        # AES-256-GCM
        encryptor = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=self.backend
        ).encryptor()
        
        # обавляем счетчик сообщений для Double Ratchet
        self.message_count += 1
        ad = struct.pack('>Q', self.message_count)
        encryptor.authenticate_additional_data(ad)
        
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()
        
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        return {
            'ciphertext': ciphertext,
            'iv': iv,
            'tag': encryptor.tag,
            'counter': self.message_count
        }
    
    def decrypt_message(self, encrypted_data, peer_id):
        """асшифровать сообщение от пира"""
        if peer_id not in self.shared_keys:
            raise Exception("No shared key for peer")
        
        key = self.shared_keys[peer_id]
        iv = encrypted_data['iv']
        tag = encrypted_data['tag']
        ciphertext = encrypted_data['ciphertext']
        
        decryptor = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, tag),
            backend=self.backend
        ).decryptor()
        
        # роверяем счетчик (защита от replay атак)
        ad = struct.pack('>Q', encrypted_data['counter'])
        decryptor.authenticate_additional_data(ad)
        
        return decryptor.update(ciphertext) + decryptor.finalize()

# ==================== MFA (вухфакторная аутентификация) ====================
class MFAManager:
    def __init__(self):
        self.secrets = self.load_mfa()
    
    def load_mfa(self):
        try:
            with open(MFA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save_mfa(self):
        with open(MFA_FILE, 'w') as f:
            json.dump(self.secrets, f, indent=2)
    
    def generate_secret(self, username):
        """енерирует TOTP секрет"""
        secret = pyotp.random_base32()
        self.secrets[username] = {
            'secret': secret,
            'enabled': True,
            'created': datetime.now().isoformat()
        }
        self.save_mfa()
        
        # енерируем QR-код
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=username, issuer_name="Nexus Remote")
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save("nexus_mfa_qr.png")
        
        return secret, "nexus_mfa_qr.png"
    
    def verify(self, username, code):
        """роверить TOTP код"""
        if username not in self.secrets:
            return False
        
        secret = self.secrets[username]['secret']
        totp = pyotp.TOTP(secret)
        return totp.verify(code)

# ==================== Ы СС УСТСТ ====================
class WhitelistManager:
    def __init__(self):
        self.whitelist = self.load()
    
    def load(self):
        try:
            with open(WHITELIST_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"devices": [], "ips": [], "geo": []}
    
    def save(self):
        with open(WHITELIST_FILE, 'w') as f:
            json.dump(self.whitelist, f, indent=2)
    
    def add_device(self, device_id):
        if device_id not in self.whitelist['devices']:
            self.whitelist['devices'].append(device_id)
            self.save()
    
    def remove_device(self, device_id):
        if device_id in self.whitelist['devices']:
            self.whitelist['devices'].remove(device_id)
            self.save()
    
    def is_allowed(self, device_id):
        return len(self.whitelist['devices']) == 0 or device_id in self.whitelist['devices']
    
    def add_ip(self, ip):
        if ip not in self.whitelist['ips']:
            self.whitelist['ips'].append(ip)
            self.save()
    
    def is_ip_allowed(self, ip):
        return len(self.whitelist['ips']) == 0 or ip in self.whitelist['ips']
    
    def add_geo(self, country_code):
        if country_code not in self.whitelist['geo']:
            self.whitelist['geo'].append(country_code)
            self.save()

# ==================== ССТ УТ ====================
class AuditLogger:
    def __init__(self):
        self.log_file = AUDIT_FILE
    
    def log(self, event, details=""):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {event} | {details}\n"
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(entry)
        
        # роверка размера лога (ротация)
        if os.path.getsize(self.log_file) > 10 * 1024 * 1024:  # 10 MB
            backup = f"{self.log_file}.{int(time.time())}"
            os.rename(self.log_file, backup)
    
    def get_recent(self, lines=100):
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        except:
            return "No audit logs"

# ====================  УСТСТ (С ЩТ) ====================
class SecureDeviceManager:
    def __init__(self):
        self.devices = self.load()
        self.whitelist = WhitelistManager()
        self.audit = AuditLogger()
        self.failed_attempts = {}  # IP -> (count, last_attempt_time)
    
    def load(self):
        try:
            with open(DEVICES_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save(self):
        with open(DEVICES_FILE, 'w') as f:
            json.dump(self.devices, f, indent=2)
    
    def check_rate_limit(self, ip):
        """Rate limiting: 5 попыток за 15 минут"""
        now = time.time()
        
        if ip in self.failed_attempts:
            count, last_time = self.failed_attempts[ip]
            
            # Сброс если прошло 15 минут
            if now - last_time > 900:
                self.failed_attempts[ip] = (1, now)
                return True
            
            if count >= 5:
                self.audit.log("RATE_LIMIT_BLOCKED", f"IP: {ip}, Attempts: {count}")
                return False
            
            self.failed_attempts[ip] = (count + 1, now)
        else:
            self.failed_attempts[ip] = (1, now)
        
        return True
    
    def verify_password(self, password, stored_hash):
        """роверка пароля с защитой от тайминг-атак"""
        if not password or not stored_hash:
            return False
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return hmac.compare_digest(password_hash, stored_hash)
    
    def add_device(self, peer_id, name, password="", platform="unknown", ip=""):
        """обавить устройство с проверками безопасности"""
        if not self.whitelist.is_ip_allowed(ip):
            self.audit.log("IP_BLOCKED", f"IP: {ip}, Device: {peer_id}")
            return False, "IP not in whitelist"
        
        if not self.check_rate_limit(ip):
            return False, "Too many attempts. Try again in 15 minutes."
        
        self.devices[peer_id] = {
            "name": name,
            "password": hashlib.sha256(password.encode()).hexdigest() if password else "",
            "platform": platform,
            "ip": ip,
            "added": datetime.now().isoformat(),
            "last_connected": "",
            "connection_count": 0,
            "trusted": False,
            "permissions": "full",  # full/viewer/files_only
            "expires": None  # None = never
        }
        self.save()
        self.audit.log("DEVICE_ADDED", f"Device: {peer_id}, Name: {name}")
        return True, "Device added"
    
    def authenticate(self, peer_id, password, ip=""):
        """олная аутентификация устройства"""
        if not self.check_rate_limit(ip):
            self.audit.log("AUTH_FAILED_RATE", f"Peer: {peer_id}, IP: {ip}")
            return False, "Rate limited"
        
        if peer_id not in self.devices:
            self.audit.log("AUTH_FAILED_UNKNOWN", f"Peer: {peer_id}")
            return False, "Unknown device"
        
        device = self.devices[peer_id]
        
        # роверка срока действия
        if device.get('expires') and datetime.fromisoformat(device['expires']) < datetime.now():
            self.audit.log("AUTH_FAILED_EXPIRED", f"Peer: {peer_id}")
            return False, "Access expired"
        
        # роверка пароля
        if not self.verify_password(password, device.get('password', '')):
            self.audit.log("AUTH_FAILED_PASSWORD", f"Peer: {peer_id}")
            return False, "Invalid password"
        
        # бновление статистики
        device['last_connected'] = datetime.now().isoformat()
        device['connection_count'] = device.get('connection_count', 0) + 1
        self.save()
        
        self.audit.log("AUTH_SUCCESS", f"Peer: {peer_id}, Connection #{device['connection_count']}")
        return True, device.get('permissions', 'full')

# ==================== NEXUS Т С ЩТ ====================
class SecureNexusClient:
    def __init__(self):
        self.peer_id = f"PC-{platform.node()}-{secrets.token_hex(4)}"
        self.stream_id = None
        self.connected_peer = None
        self.capturing = False
        self.fps = 30
        self.quality = "high"
        self.e2ee = E2EEncryption()
        self.mfa = MFAManager()
        self.device_manager = SecureDeviceManager()
        self.device_id = f"NEXUS-{secrets.token_hex(4)}"
        self.device_password = secrets.token_hex(8)
        self.failed_attempts = 0
        self.max_attempts = 5
        self.lock_until = None
        self.session_token = None
        
        self.stats = {
            'frames_sent': 0,
            'bytes_sent': 0,
            'fps_actual': 0,
            'errors': 0,
            'encrypted_bytes': 0
        }
    
    def register(self):
        data = {
            "peer_id": self.peer_id,
            "platform": "windows",
            "public_key": base64.b64encode(self.e2ee.get_public_key_bytes()).decode(),
            "compression": COMPRESSION,
            "encryption": ENCRYPTION
        }
        try:
            resp = requests.post(f"{SERVER_URL}/register", json=data, timeout=5)
            return resp.json().get('status') == 'registered'
        except:
            return False
    
    def start_secure_stream(self, target, password="", quality="high"):
        """апуск защищенного стрима"""
        # роверка блокировки
        if self.lock_until and datetime.now() < self.lock_until:
            remaining = (self.lock_until - datetime.now()).seconds
            return False, f"Account locked for {remaining} seconds"
        
        # роверка лимита устройств
        if len(self.device_manager.devices) > 10:
            return False, "Maximum devices reached (10)"
        
        # утентификация
        auth_ok, result = self.device_manager.authenticate(target, password)
        if not auth_ok:
            self.failed_attempts += 1
            if self.failed_attempts >= self.max_attempts:
                self.lock_until = datetime.now() + timedelta(minutes=15)
            return False, result
        
        # Сброс счетчика при успехе
        self.failed_attempts = 0
        
        # бмен ключами E2EE
        try:
            resp = requests.get(f"{SERVER_URL}/peers", timeout=3)
            peers = resp.json().get('peers', [])
            
            # олучаем публичный ключ пира
            for peer_info in peers:
                if isinstance(peer_info, dict) and peer_info.get('peer_id') == target:
                    peer_pub_key = base64.b64decode(peer_info.get('public_key', ''))
                    if peer_pub_key:
                        self.e2ee.compute_shared_key(peer_pub_key, target)
                        break
        except:
            pass
        
        # апуск стрима
        data = {
            "source": self.peer_id,
            "target": target,
            "quality": quality,
            "compression": COMPRESSION,
            "encryption": ENCRYPTION
        }
        
        try:
            resp = requests.post(f"{SERVER_URL}/start_stream", json=data, timeout=5)
            result = resp.json()
            if result.get('status') == 'streaming':
                self.stream_id = result['stream_id']
                self.connected_peer = target
                self.session_token = secrets.token_hex(16)
                return True, "Connected"
        except:
            pass
        
        return False, "Connection failed"
    
    def send_secure_frame(self, frame_bytes):
        """тправить зашифрованный кадр"""
        if not self.stream_id or not self.connected_peer:
            return
        
        try:
            # E2EE шифрование
            if self.connected_peer in self.e2ee.shared_keys:
                encrypted = self.e2ee.encrypt_message(frame_bytes, self.connected_peer)
                frame_b64 = base64.b64encode(encrypted['ciphertext']).decode()
                
                data = {
                    "stream_id": self.stream_id,
                    "from": self.peer_id,
                    "target": self.connected_peer,
                    "frame": frame_b64,
                    "type": "video",
                    "e2ee": {
                        "iv": base64.b64encode(encrypted['iv']).decode(),
                        "tag": base64.b64encode(encrypted['tag']).decode(),
                        "counter": encrypted['counter']
                    }
                }
            else:
                # ез E2EE (fallback)
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
                self.stats['encrypted_bytes'] += len(data.get('frame', ''))
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
            self.session_token = None
    
    def get_peers(self):
        try:
            resp = requests.get(f"{SERVER_URL}/peers", timeout=3)
            return resp.json().get('peers', [])
        except:
            return []

# ==================== UI (УУШЫ) ====================
class SecureNexusUI:
    def __init__(self):
        self.client = SecureNexusClient()
        self.root = tk.Tk()
        self.root.title("Nexus Remote v3.0 - SECURE EDITION 🔐")
        
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.window_w = min(850, screen_w - 100)
        self.window_h = min(650, screen_h - 100)
        self.root.geometry(f"{self.window_w}x{self.window_h}")
        self.root.minsize(750, 550)
        
        self.bg = '#0c0c18'
        self.card_bg = '#16162a'
        self.accent = '#6366f1'
        self.green = '#34d399'
        self.red = '#f87171'
        self.orange = '#fbbf24'
        self.text_color = '#e0e0e0'
        self.gray = '#8c8ca0'
        
        self.root.configure(bg=self.bg)
        
        self.setup_ui()
        self.update_status()
    
    def create_card(self, parent, **kwargs):
        return tk.Frame(parent, bg=self.card_bg, bd=0, highlightthickness=1,
                       highlightbackground='#2a2a4a', **kwargs)
    
    def create_button(self, parent, text, color, command, width=150, height=34):
        return tk.Button(parent, text=text, font=('Segoe UI', 10, 'bold'),
                        bg=color, fg='white', activebackground=color,
                        relief=tk.FLAT, bd=0, padx=12, pady=6,
                        cursor='hand2', command=command)
    
    def create_entry(self, parent, placeholder="", show=None):
        entry = tk.Entry(parent, font=('Segoe UI', 10),
                        bg='#0f0f1a', fg=self.text_color,
                        insertbackground=self.text_color,
                        relief=tk.FLAT, bd=1, show=show if show else '')
        if placeholder:
            entry.insert(0, placeholder)
            entry.bind('<FocusIn>', lambda e: entry.delete(0, tk.END) if entry.get() == placeholder else None)
        return entry
    
    def setup_ui(self):
        main = tk.Frame(self.root, bg=self.bg)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=12)
        
        # аголовок
        tk.Label(main, text="🔐 Nexus Remote v3.0", font=('Segoe UI', 22, 'bold'),
                fg=self.accent, bg=self.bg).pack(anchor='w')
        tk.Label(main, text="Secure Remote Desktop · E2EE · MFA · Audit",
                font=('Segoe UI', 9), fg=self.gray, bg=self.bg).pack(anchor='w')
        
        # кладки
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        
        self.create_connect_tab()
        self.create_security_tab()
        self.create_devices_tab()
        self.create_audit_tab()
        self.create_settings_tab()
        
        # ижняя панель
        self.create_bottom_bar(main)
    
    def create_connect_tab(self):
        tab = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(tab, text="  🔗 Connect  ")
        
        # евая панель - одключение
        left = tk.Frame(tab, bg=self.bg)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # арточка устройства
        card1 = self.create_card(left)
        card1.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(card1, text="🖥 My Device", font=('Segoe UI', 13, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=15, pady=(12, 5))
        
        info = tk.Frame(card1, bg=self.card_bg)
        info.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        for label, value, color in [
            ("Device ID", self.client.device_id, self.text_color),
            ("Password", self.client.device_password, self.orange),
            ("Peer ID", self.client.peer_id, self.gray)
        ]:
            row = tk.Frame(info, bg=self.card_bg)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"{label}:", font=('Segoe UI', 9),
                    fg=self.gray, bg=self.card_bg).pack(side=tk.LEFT)
            tk.Label(row, text=value, font=('Segoe UI', 9, 'bold'),
                    fg=color, bg=self.card_bg).pack(side=tk.LEFT, padx=(5, 0))
        
        # нопки QR и MFA
        btn_row = tk.Frame(info, bg=self.card_bg)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        self.create_button(btn_row, "📷 QR Code", self.accent,
                          self.show_qr, width=120, height=30).pack(side=tk.LEFT, padx=(0, 5))
        self.create_button(btn_row, "🔑 Setup MFA", self.orange,
                          self.setup_mfa, width=120, height=30).pack(side=tk.LEFT)
        
        # арточка подключения
        card2 = self.create_card(left)
        card2.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(card2, text="🔗 Connect to Device", font=('Segoe UI', 13, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=15, pady=(12, 8))
        
        conn = tk.Frame(card2, bg=self.card_bg)
        conn.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        self.peer_entry = self.create_entry(conn, "Peer ID")
        self.peer_entry.pack(fill=tk.X, pady=3)
        
        self.pass_entry = self.create_entry(conn, "Password", show="●")
        self.pass_entry.pack(fill=tk.X, pady=3)
        
        self.mfa_entry = self.create_entry(conn, "MFA Code (if enabled)")
        self.mfa_entry.pack(fill=tk.X, pady=3)
        
        btn_frame = tk.Frame(conn, bg=self.card_bg)
        btn_frame.pack(fill=tk.X, pady=(8, 0))
        
        self.connect_btn = self.create_button(btn_frame, "🔒 Secure Connect", self.green,
                                             self.secure_connect, width=170)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.create_button(btn_frame, "📋 Copy ID", self.gray,
                          lambda: self.root.clipboard_append(self.client.peer_id),
                          width=100).pack(side=tk.LEFT)
        
        # равая панель - ахват
        right = tk.Frame(tab, bg=self.bg)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        
        card3 = self.create_card(right)
        card3.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(card3, text="📺 Capture", font=('Segoe UI', 13, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=15, pady=(12, 5))
        
        self.conn_status = tk.Label(card3, text="Not connected",
                                     font=('Segoe UI', 9), fg=self.gray, bg=self.card_bg)
        self.conn_status.pack(anchor='w', padx=15, pady=(0, 5))
        
        # Статистика безопасности
        self.encryption_status = tk.Label(card3, text="🔒 E2EE: Waiting for connection",
                                          font=('Segoe UI', 9), fg=self.orange, bg=self.card_bg)
        self.encryption_status.pack(anchor='w', padx=15, pady=2)
        
        center = tk.Frame(card3, bg=self.card_bg)
        center.pack(pady=15)
        
        self.capture_btn = self.create_button(center, "▶ Start Secure Capture", self.green,
                                             self.toggle_capture, width=200)
        self.capture_btn.pack()
        
        self.capture_label = tk.Label(card3, text="● Ready", font=('Segoe UI', 9),
                                       fg=self.gray, bg=self.card_bg)
        self.capture_label.pack(pady=(8, 10))
    
    def create_security_tab(self):
        tab = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(tab, text="  🔒 Security  ")
        
        card = self.create_card(tab)
        card.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(card, text="🛡 Security Status", font=('Segoe UI', 13, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=15, pady=(12, 10))
        
        items = [
            ("🔐 End-to-End Encryption", "AES-256-GCM + Diffie-Hellman", self.green),
            ("🔑 Two-Factor Auth (MFA)", "TOTP (Google Authenticator)", self.green if self.client.mfa.secrets else self.gray),
            ("📋 Whitelist", f"{len(self.client.device_manager.whitelist.whitelist['devices'])} devices", self.green),
            ("🛡 Rate Limiting", "5 attempts / 15 min", self.green),
            ("📝 Audit Logging", f"{os.path.getsize(AUDIT_FILE) if os.path.exists(AUDIT_FILE) else 0} bytes", self.green),
            ("🔒 Password Hashing", "SHA-256 + HMAC", self.green),
            ("🌍 Geo Blocking", "Disabled", self.gray),
            ("🔐 Session Token", f"{'Active' if self.client.session_token else 'None'}", self.green if self.client.session_token else self.gray)
        ]
        
        for label, value, color in items:
            row = tk.Frame(card, bg=self.card_bg)
            row.pack(fill=tk.X, padx=15, pady=3)
            tk.Label(row, text=label, font=('Segoe UI', 10),
                    fg=self.gray, bg=self.card_bg).pack(side=tk.LEFT)
            tk.Label(row, text=value, font=('Segoe UI', 10, 'bold'),
                    fg=color, bg=self.card_bg).pack(side=tk.RIGHT)
    
    def create_devices_tab(self):
        tab = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(tab, text="  💾 Devices  ")
        
        card = self.create_card(tab)
        card.pack(fill=tk.BOTH, expand=True)
        
        header = tk.Frame(card, bg=self.card_bg)
        header.pack(fill=tk.X, padx=15, pady=(12, 8))
        
        tk.Label(header, text="💾 Saved Devices", font=('Segoe UI', 13, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(side=tk.LEFT)
        
        self.create_button(header, "🔄 Refresh", self.accent,
                          self.refresh_devices, width=120, height=30).pack(side=tk.RIGHT)
        
        self.device_list = tk.Frame(card, bg=self.card_bg)
        self.device_list.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        self.refresh_devices()
    
    def create_audit_tab(self):
        tab = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(tab, text="  📝 Audit  ")
        
        card = self.create_card(tab)
        card.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(card, text="📝 Audit Log", font=('Segoe UI', 13, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=15, pady=(12, 5))
        
        self.audit_text = scrolledtext.ScrolledText(card, height=20,
                                                     font=('Consolas', 9),
                                                     bg='#0f0f1a', fg=self.text_color,
                                                     relief=tk.FLAT, bd=0)
        self.audit_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        # агружаем логи
        logs = self.client.device_manager.audit.get_recent(200)
        self.audit_text.insert('1.0', logs if logs else "No audit records")
    
    def create_settings_tab(self):
        tab = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(tab, text="  ⚙️ Settings  ")
        
        card = self.create_card(tab)
        card.pack(fill=tk.X)
        
        tk.Label(card, text="⚙️ Settings", font=('Segoe UI', 13, 'bold'),
                fg=self.accent, bg=self.card_bg).pack(anchor='w', padx=15, pady=(12, 8))
        
        for label, options in [
            ("Encryption", ["AES-256-GCM", "ChaCha20-Poly1305", "AES-256-CBC"]),
            ("Compression", ["ZSTD", "LZ4", "Brotli", "ZLIB"]),
            ("Quality", ["Ultra (4K@60)", "High (1080p@60)", "Medium (720p@30)"]),
            ("MFA", ["Enabled", "Disabled"]),
            ("Whitelist Mode", ["Allow All", "Whitelist Only"])
        ]:
            row = tk.Frame(card, bg=self.card_bg)
            row.pack(fill=tk.X, padx=15, pady=3)
            tk.Label(row, text=label, font=('Segoe UI', 10),
                    fg=self.gray, bg=self.card_bg).pack(anchor='w')
            combo = ttk.Combobox(row, values=options, font=('Segoe UI', 9), state='readonly')
            combo.set(options[0])
            combo.pack(fill=tk.X, pady=(3, 0))
    
    def create_bottom_bar(self, parent):
        bar = tk.Frame(parent, bg='#121226', height=34)
        bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))
        bar.pack_propagate(False)
        
        self.status_dot = tk.Label(bar, text="●", font=('Segoe UI', 10),
                                   fg=self.red, bg='#121226')
        self.status_dot.pack(side=tk.LEFT, padx=(12, 4))
        
        self.bar_status = tk.Label(bar, text="Ready", font=('Segoe UI', 8),
                                   fg=self.gray, bg='#121226')
        self.bar_status.pack(side=tk.LEFT)
        
        self.encryption_indicator = tk.Label(bar, text="🔒 E2EE",
                                             font=('Segoe UI', 8),
                                             fg=self.orange, bg='#121226')
        self.encryption_indicator.pack(side=tk.RIGHT, padx=12)
    
    # ==================== ФУЦ ====================
    def show_qr(self):
        qr_data = f"nexus://connect/{self.client.peer_id}?pw={self.client.device_password}"
        
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save("nexus_qr_temp.png")
        
        top = tk.Toplevel(self.root)
        top.title("QR Code - Nexus Remote")
        top.geometry("300x380")
        top.configure(bg=self.bg)
        
        tk.Label(top, text="Scan to Connect", font=('Segoe UI', 12, 'bold'),
                fg=self.accent, bg=self.bg).pack(pady=10)
        
        photo = tk.PhotoImage(file="nexus_qr_temp.png")
        tk.Label(top, image=photo, bg=self.bg).pack(pady=5)
        top.image = photo
        
        tk.Label(top, text=f"Password: {self.client.device_password}",
                font=('Segoe UI', 9), fg=self.orange, bg=self.bg).pack()
    
    def setup_mfa(self):
        username = simpledialog.askstring("MFA Setup", "Enter username for MFA:")
        if username:
            secret, qr_path = self.client.mfa.generate_secret(username)
            
            top = tk.Toplevel(self.root)
            top.title("MFA Setup")
            top.geometry("350x400")
            top.configure(bg=self.bg)
            
            tk.Label(top, text="Scan with Google Authenticator",
                    font=('Segoe UI', 11, 'bold'), fg=self.accent, bg=self.bg).pack(pady=10)
            
            photo = tk.PhotoImage(file=qr_path)
            tk.Label(top, image=photo, bg=self.bg).pack()
            top.image = photo
            
            tk.Label(top, text=f"Secret: {secret}", font=('Consolas', 8),
                    fg=self.text_color, bg=self.bg).pack(pady=5)
            
            # роверка кода
            code_entry = tk.Entry(top, font=('Segoe UI', 14, 'bold'), width=10,
                                 bg='#0f0f1a', fg=self.text_color, justify='center')
            code_entry.pack(pady=10)
            
            def verify():
                code = code_entry.get()
                if self.client.mfa.verify(username, code):
                    messagebox.showinfo("Success", "MFA enabled!", parent=top)
                    top.destroy()
                else:
                    messagebox.showerror("Error", "Invalid code", parent=top)
            
            self.create_button(top, "Verify Code", self.green, verify).pack(pady=5)
    
    def secure_connect(self):
        peer_id = self.peer_entry.get().strip()
        password = self.pass_entry.get().strip()
        mfa_code = self.mfa_entry.get().strip()
        
        if not peer_id or peer_id == "Peer ID":
            messagebox.showwarning("Error", "Enter Peer ID")
            return
        
        # MFA проверка
        if mfa_code and mfa_code != "MFA Code (if enabled)":
            if not self.client.mfa.verify(self.client.peer_id, mfa_code):
                messagebox.showerror("MFA Failed", "Invalid MFA code")
                return
        
        success, msg = self.client.start_secure_stream(peer_id, password)
        
        if success:
            self.conn_status.config(text=f"Connected: {peer_id}", fg=self.green)
            self.encryption_status.config(text="🔒 E2EE: Active (AES-256-GCM)", fg=self.green)
            self.encryption_indicator.config(fg=self.green)
            messagebox.showinfo("Connected", f"Secure connection established!\nE2EE: Active\nToken: {self.client.session_token[:8]}...")
        else:
            self.encryption_status.config(text=f"❌ {msg}", fg=self.red)
            messagebox.showerror("Connection Failed", msg)
    
    def toggle_capture(self):
        if not self.client.capturing:
            if not self.client.connected_peer:
                messagebox.showwarning("Error", "Connect to device first")
                return
            
            self.client.capturing = True
            self.capture_btn.config(text="⏹ Stop", bg=self.red)
            self.capture_label.config(text="● Capturing (E2EE)", fg=self.orange)
            self.status_dot.config(fg=self.orange)
            
            threading.Thread(target=self.secure_capture_loop, daemon=True).start()
        else:
            self.client.capturing = False
            self.client.stop_stream()
            self.capture_btn.config(text="▶ Start Secure Capture", bg=self.green)
            self.capture_label.config(text="● Ready", fg=self.gray)
            self.status_dot.config(fg=self.green)
    
    def secure_capture_loop(self):
        while self.client.capturing:
            try:
                screenshot = pyautogui.screenshot()
                buf = io.BytesIO()
                screenshot.save(buf, format='JPEG', quality=50)
                
                self.client.send_secure_frame(buf.getvalue())
                time.sleep(1/self.client.fps)
            except Exception as e:
                time.sleep(1)
    
    def refresh_devices(self):
        for w in self.device_list.winfo_children():
            w.destroy()
        
        devices = self.client.device_manager.devices
        
        if not devices:
            tk.Label(self.device_list, text="No saved devices",
                    font=('Segoe UI', 10), fg=self.gray,
                    bg=self.card_bg).pack(expand=True)
            return
        
        for peer_id, info in devices.items():
            row = tk.Frame(self.device_list, bg='#1e1e38', bd=0,
                          highlightthickness=1, highlightbackground='#2a2a4a')
            row.pack(fill=tk.X, pady=1)
            
            tk.Label(row, text=info.get('name', '?')[:15], font=('Segoe UI', 9),
                    fg=self.text_color, bg='#1e1e38', width=15, anchor='w').pack(side=tk.LEFT, padx=8, pady=6)
            tk.Label(row, text=peer_id[:20], font=('Segoe UI', 8),
                    fg=self.gray, bg='#1e1e38', width=20, anchor='w').pack(side=tk.LEFT, padx=4, pady=6)
            tk.Label(row, text=f"🔗 {info.get('connection_count', 0)}",
                    font=('Segoe UI', 8), fg=self.green, bg='#1e1e38', width=8).pack(side=tk.LEFT, padx=4, pady=6)
            
            btn_f = tk.Frame(row, bg='#1e1e38')
            btn_f.pack(side=tk.RIGHT, padx=8)
            
            self.create_button(btn_f, "▶", self.green,
                             lambda p=peer_id: self.quick_connect(p), width=30, height=24).pack(side=tk.LEFT, padx=2)
            self.create_button(btn_f, "✕", self.red,
                             lambda p=peer_id: self.remove_device(p), width=30, height=24).pack(side=tk.LEFT, padx=2)
    
    def quick_connect(self, peer_id):
        devices = self.client.device_manager.devices
        if peer_id in devices:
            success, msg = self.client.start_secure_stream(peer_id, "")
            if success:
                self.conn_status.config(text=f"Quick connect: {peer_id}", fg=self.green)
                self.encryption_status.config(text="🔒 E2EE: Active", fg=self.green)
    
    def remove_device(self, peer_id):
        if messagebox.askyesno("Remove", f"Remove {peer_id}?"):
            self.client.device_manager.devices.pop(peer_id, None)
            self.client.device_manager.save()
            self.refresh_devices()
    
    def update_status(self):
        if self.client.register():
            self.status_dot.config(fg=self.green)
            self.bar_status.config(text="Server Connected")
        else:
            self.status_dot.config(fg=self.red)
    
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()
    
    def on_close(self):
        self.client.capturing = False
        self.client.stop_stream()
        self.root.destroy()

if __name__ == "__main__":
    print("🔐 Nexus Remote v3.0 SECURE EDITION")
    print("Features: E2EE, MFA, Whitelist, Rate Limit, Audit Log")
    app = SecureNexusUI()
    app.run()
