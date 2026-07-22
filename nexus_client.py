#!/usr/bin/env python3
# nexus_client.py - Универсальный клиент Nexus Remote
# оддержка: Windows, Linux, macOS
import requests
import json
import time
import base64
import platform
import threading
import sys

SERVER_URL = "https://nexus-remote.onrender.com"

class NexusClient:
    def __init__(self, peer_id, server_url=SERVER_URL):
        self.peer_id = peer_id
        self.server_url = server_url
        self.platform = self._detect_platform()
        self.running = False
        self.stream_id = None
        
    def _detect_platform(self):
        system = platform.system().lower()
        if system == 'windows':
            return 'windows'
        elif system == 'darwin':
            return 'macos'
        else:
            return 'linux'
    
    def register(self):
        """егистрация на сервере"""
        data = {
            "peer_id": self.peer_id,
            "platform": self.platform,
            "codec": "auto",
            "resolution": "1080p",
            "fps": 30
        }
        resp = requests.post(f"{self.server_url}/register", json=data)
        result = resp.json()
        print(f"[+] Registered as {self.peer_id} ({self.platform})")
        print(f"[+] Codec: {result.get('codec_config', {}).get('primary', 'auto')}")
        return result
    
    def start_stream(self, target_peer, quality="auto"):
        """ачать стриминг экрана"""
        data = {
            "source": self.peer_id,
            "target": target_peer,
            "quality": quality
        }
        resp = requests.post(f"{self.server_url}/start_stream", json=data)
        result = resp.json()
        if result.get('status') == 'streaming':
            self.stream_id = result['stream_id']
            print(f"[STREAM] Started: {result['config']['resolution']} @ {result['config']['fps']}fps")
        return result
    
    def send_frame(self, frame_data, frame_type="video"):
        """тправить кадр"""
        if not self.stream_id:
            return
        
        # одируем кадр в base64
        if isinstance(frame_data, bytes):
            frame_data = base64.b64encode(frame_data).decode()
        
        data = {
            "stream_id": self.stream_id,
            "from": self.peer_id,
            "target": self._get_target(),
            "frame": frame_data,
            "type": frame_type
        }
        resp = requests.post(f"{self.server_url}/send_frame", json=data)
        return resp.json()
    
    def get_frame(self, peer_id):
        """олучить кадр для отображения"""
        data = {"peer_id": peer_id}
        resp = requests.post(f"{self.server_url}/get_frame", json=data)
        result = resp.json()
        if result.get('type') != 'empty':
            # екодируем base64
            frame_data = result.get('data', '')
            if frame_data:
                return base64.b64decode(frame_data)
        return None
    
    def stop_stream(self):
        """становить стриминг"""
        if self.stream_id:
            data = {"stream_id": self.stream_id}
            requests.post(f"{self.server_url}/stop_stream", json=data)
            self.stream_id = None
            print("[STREAM] Stopped")
    
    def capture_screen(self):
        """ахват экрана (зависит от платформы)"""
        if self.platform == 'windows':
            return self._capture_windows()
        elif self.platform == 'linux':
            return self._capture_linux()
        elif self.platform == 'macos':
            return self._capture_macos()
    
    def _capture_windows(self):
        try:
            import pyautogui
            import io
            screenshot = pyautogui.screenshot()
            buf = io.BytesIO()
            screenshot.save(buf, format='JPEG', quality=70)
            return buf.getvalue()
        except ImportError:
            print("[-] Install: pip install pyautogui pillow")
            return None
    
    def _capture_linux(self):
        try:
            import subprocess
            result = subprocess.run(['import', '-window', 'root', 'jpeg:-'], 
                                  capture_output=True, shell=True)
            return result.stdout
        except:
            return None
    
    def _capture_macos(self):
        try:
            import subprocess
            result = subprocess.run(['screencapture', '-x', '-t', 'jpg', '-'], 
                                  capture_output=True)
            return result.stdout
        except:
            return None

# ример использования
if __name__ == "__main__":
    peer_id = sys.argv[1] if len(sys.argv) > 1 else f"Device-{int(time.time())}"
    
    client = NexusClient(peer_id)
    client.register()
    
    print(f"\nCommands: start <target> | stop | quit")
    
    while True:
        cmd = input("> ").strip().split()
        if not cmd:
            continue
        
        if cmd[0] == 'start' and len(cmd) > 1:
            target = cmd[1]
            quality = cmd[2] if len(cmd) > 2 else 'auto'
            client.start_stream(target, quality)
            
            # апускаем захват экрана в отдельном потоке
            def capture_loop():
                while client.stream_id:
                    frame = client.capture_screen()
                    if frame:
                        client.send_frame(frame)
                    time.sleep(1/30)  # 30 FPS
            
            threading.Thread(target=capture_loop, daemon=True).start()
            print("[CAPTURE] Screen capture started")
        
        elif cmd[0] == 'stop':
            client.stop_stream()
        
        elif cmd[0] == 'quit':
            break
