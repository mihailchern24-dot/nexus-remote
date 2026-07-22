#!/usr/bin/env python3
# nexus_agent.py - ниверсальный агент Nexus Remote
import requests
import json
import time
import base64
import threading
import os
import sys
import platform
from datetime import datetime

SERVER_URL = "https://nexus-remote.onrender.com"
PEER_ID = f"agent-{platform.node()}-{int(time.time())}"
PLATFORM = platform.system().lower()

class NexusAgent:
    """азовый агент для всех платформ"""
    
    def __init__(self, server_url=SERVER_URL, peer_id=None):
        self.server_url = server_url
        self.peer_id = peer_id or PEER_ID
        self.platform = PLATFORM
        self.running = False
        self.stream_id = None
        self.connected_peer = None
        self.compression = "zstd"
        self.encryption = "aes_gcm"
        self.quality = "high"
        self.fps = 30
        self.capture_method = "none"
        
        self.stats = {
            'frames_sent': 0,
            'frames_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'start_time': None,
            'errors': 0
        }
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def register(self):
        """егистрация на сервере"""
        data = {
            "peer_id": self.peer_id,
            "platform": self.platform,
            "compression": self.compression,
            "encryption": self.encryption,
            "hostname": platform.node(),
            "version": "2.1.0"
        }
        
        try:
            resp = requests.post(f"{self.server_url}/register", json=data, timeout=10)
            result = resp.json()
            
            if result.get('status') == 'registered':
                self.log(f"Registered as {self.peer_id} ({self.platform})")
                self.log(f"Codec: {result.get('codec_config', {}).get('primary', 'auto')}")
                return True
            else:
                self.log(f"Registration failed: {result}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Registration error: {e}", "ERROR")
            return False
    
    def start_stream(self, target_peer, quality="high", compression="auto", encryption="aes_gcm"):
        """ачать стриминг"""
        data = {
            "source": self.peer_id,
            "target": target_peer,
            "quality": quality,
            "compression": compression,
            "encryption": encryption
        }
        
        try:
            resp = requests.post(f"{self.server_url}/start_stream", json=data, timeout=10)
            result = resp.json()
            
            if result.get('status') == 'streaming':
                self.stream_id = result['stream_id']
                self.connected_peer = target_peer
                self.stats['start_time'] = time.time()
                self.log(f"Stream started: {result['quality']['resolution']} @ {result['quality']['fps']}fps")
                return True
            else:
                self.log(f"Stream failed: {result}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Stream error: {e}", "ERROR")
            return False
    
    def send_frame(self, frame_data, frame_type="video"):
        """тправить кадр"""
        if not self.stream_id:
            return False
        
        try:
            if isinstance(frame_data, bytes):
                frame_b64 = base64.b64encode(frame_data).decode()
            else:
                frame_b64 = frame_data
            
            data = {
                "stream_id": self.stream_id,
                "from": self.peer_id,
                "target": self.connected_peer,
                "frame": frame_b64,
                "type": frame_type,
                "compression": self.compression,
                "encryption": self.encryption
            }
            
            resp = requests.post(f"{self.server_url}/send_frame", json=data, timeout=10)
            result = resp.json()
            
            if result.get('status') == 'sent':
                self.stats['frames_sent'] += 1
                self.stats['bytes_sent'] += len(frame_b64)
                return True
            else:
                self.stats['errors'] += 1
                return False
        except Exception as e:
            self.stats['errors'] += 1
            return False
    
    def get_frame(self):
        """олучить кадр"""
        try:
            data = {"peer_id": self.peer_id}
            resp = requests.post(f"{self.server_url}/get_frame", json=data, timeout=10)
            result = resp.json()
            
            if result.get('type') != 'empty' and result.get('data'):
                frame_b64 = result.get('data', '')
                if frame_b64:
                    frame_bytes = base64.b64decode(frame_b64)
                    self.stats['frames_received'] += 1
                    self.stats['bytes_received'] += len(frame_bytes)
                    return {
                        'data': frame_bytes,
                        'from': result.get('from'),
                        'type': result.get('type')
                    }
            return None
        except:
            return None
    
    def stop_stream(self):
        """становить стрим"""
        if self.stream_id:
            try:
                data = {"stream_id": self.stream_id}
                requests.post(f"{self.server_url}/stop_stream", json=data, timeout=10)
                self.log(f"Stream stopped. Frames: {self.stats['frames_sent']}, "
                        f"Data: {self.stats['bytes_sent'] // 1024} KB")
            except:
                pass
            self.stream_id = None
            self.connected_peer = None
    
    def get_peers(self):
        """олучить список пиров"""
        try:
            resp = requests.get(f"{self.server_url}/peers", timeout=10)
            result = resp.json()
            return result.get('peers', [])
        except:
            return []
    
    def get_stats(self):
        """олучить статистику"""
        uptime = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
        return {
            **self.stats,
            'uptime_seconds': int(uptime),
            'fps_actual': round(self.stats['frames_sent'] / uptime, 1) if uptime > 0 else 0,
            'bandwidth_kbps': round((self.stats['bytes_sent'] * 8 / 1024) / uptime, 1) if uptime > 0 else 0
        }
    
    def run(self):
        """сновной цикл"""
        self.running = True
        self.log(f"Agent {self.peer_id} started on {self.platform}")
        
        if not self.register():
            self.log("Failed to register", "ERROR")
            return
        
        print("\nCommands: start <peer> | stop | peers | stats | quit\n")
        
        # оток для получения кадров
        def receive_loop():
            while self.running:
                frame = self.get_frame()
                if frame and hasattr(self, 'on_frame_received'):
                    self.on_frame_received(frame)
                time.sleep(1/self.fps)
        
        threading.Thread(target=receive_loop, daemon=True).start()
        
        # оток для отправки кадров
        def send_loop():
            while self.running:
                if self.stream_id:
                    self.capture_and_send()
                time.sleep(1/self.fps)
        
        threading.Thread(target=send_loop, daemon=True).start()
        
        # онсольный интерфейс
        while self.running:
            try:
                cmd = input("> ").strip().split()
                if not cmd:
                    continue
                
                if cmd[0] == 'start' and len(cmd) > 1:
                    target = cmd[1]
                    quality = cmd[2] if len(cmd) > 2 else 'high'
                    self.start_stream(target, quality)
                
                elif cmd[0] == 'stop':
                    self.stop_stream()
                
                elif cmd[0] == 'peers':
                    peers = self.get_peers()
                    print(f"Online peers ({len(peers)}): {', '.join(peers)}")
                
                elif cmd[0] == 'stats':
                    stats = self.get_stats()
                    print(json.dumps(stats, indent=2))
                
                elif cmd[0] == 'quit':
                    break
                
                else:
                    print("Commands: start <peer> | stop | peers | stats | quit")
            
            except KeyboardInterrupt:
                break
        
        self.stop_stream()
        print("Agent stopped.")
    
    def capture_and_send(self):
        """ахват и отправка (переопределяется)"""
        pass

if __name__ == "__main__":
    agent = NexusAgent()
    agent.run()
