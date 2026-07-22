#!/usr/bin/env python3
# windows_agent.py - Windows агент с захватом экрана
import sys
import os

# обавляем родительскую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus_agent import NexusAgent
import time
import threading
import io

class WindowsAgent(NexusAgent):
    """Windows агент с захватом экрана через PIL/pyautogui"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.capture_method = None
        self.screen = None
    
    def init_capture(self):
        """нициализация захвата экрана"""
        try:
            import pyautogui
            self.screen = pyautogui
            self.capture_method = "pyautogui"
            self.log(f"Capture method: {self.capture_method}")
            return True
        except ImportError:
            self.log("pyautogui not available", "WARN")
            
            try:
                from PIL import ImageGrab
                self.screen = ImageGrab
                self.capture_method = "PIL"
                self.log(f"Capture method: {self.capture_method}")
                return True
            except ImportError:
                self.log("PIL not available. Install: pip install pyautogui pillow", "ERROR")
                return False
    
    def capture_screen(self):
        """ахват экрана"""
        try:
            if self.capture_method == "pyautogui":
                screenshot = self.screen.screenshot()
                buf = io.BytesIO()
                screenshot.save(buf, format='JPEG', quality=70)
                return buf.getvalue()
            
            elif self.capture_method == "PIL":
                screenshot = self.screen.grab()
                buf = io.BytesIO()
                screenshot.save(buf, format='JPEG', quality=70)
                return buf.getvalue()
        except Exception as e:
            return None
    
    def capture_and_send(self):
        """ахват и отправка кадра"""
        if not self.stream_id:
            return
        
        frame = self.capture_screen()
        if frame:
            self.send_frame(frame, "video")

if __name__ == "__main__":
    agent = WindowsAgent()
    
    print("""
    ╔══════════════════════════════════════╗
    ║   Windows Agent v2.1                 ║
    ║   Capture: pyautogui/PIL             ║
    ╚══════════════════════════════════════╝
    """)
    
    if agent.init_capture():
        agent.run()
    else:
        print("Install: pip install pyautogui pillow")
