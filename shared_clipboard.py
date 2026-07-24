#!/usr/bin/env python3
# shared_clipboard.py - Sync clipboard between devices
import requests
import time
import threading
import sys
import platform

SERVER = "https://nexus-remote.onrender.com"
PEER_ID = f"clipboard-{platform.node()}"

class SharedClipboard:
    def __init__(self):
        self.last_text = ""
        self.peer_text = ""
        self.running = False
    
    def register(self):
        try:
            requests.post(f"{SERVER}/register", json={"peer_id": PEER_ID, "platform": "clipboard"}, timeout=3)
        except: pass
    
    def get_clipboard(self):
        try:
            import pyperclip
            return pyperclip.paste()
        except:
            return ""
    
    def set_clipboard(self, text):
        try:
            import pyperclip
            pyperclip.copy(text)
        except: pass
    
    def sync_loop(self):
        self.running = True
        while self.running:
            try:
                current = self.get_clipboard()
                if current and current != self.last_text:
                    self.last_text = current
                    requests.post(f"{SERVER}/clipboard", json={"from": PEER_ID, "text": current}, timeout=3)
                
                resp = requests.get(f"{SERVER}/clipboard/{PEER_ID}", timeout=3)
                data = resp.json()
                if data.get('text') and data['text'] != self.peer_text:
                    self.peer_text = data['text']
                    self.set_clipboard(data['text'])
                    print(f"[Clipboard] Synced: {data['text'][:50]}...")
            except: pass
            time.sleep(1)
    
    def run(self):
        self.register()
        self.sync_loop()

if __name__ == "__main__":
    print("Nexus Shared Clipboard")
    print("Copy anything - it syncs between devices!")
    SharedClipboard().run()
