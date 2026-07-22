#!/usr/bin/env python3
# macos_agent.py - macOS агент с захватом экрана
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nexus_agent import NexusAgent
import subprocess
import io
import time

class MacOSAgent(NexusAgent):
    """macOS агент с захватом экрана"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.capture_method = None
    
    def init_capture(self):
        """нициализация захвата"""
        methods = []
        
        # screencapture (встроенный)
        if self._check_command('screencapture'):
            methods.append('screencapture')
        
        # ffmpeg с AVFoundation
        if self._check_command('ffmpeg'):
            methods.append('ffmpeg')
        
        # pyautogui
        try:
            import pyautogui
            methods.append('pyautogui')
        except:
            pass
        
        if methods:
            self.capture_method = methods[0]
            self.log(f"Capture methods: {', '.join(methods)}")
            self.log(f"Using: {self.capture_method}")
            return True
        else:
            self.log("No capture method available!", "ERROR")
            return False
    
    def _check_command(self, cmd):
        try:
            subprocess.run(['which', cmd], capture_output=True, check=True)
            return True
        except:
            return False
    
    def capture_screen(self):
        """ахват экрана"""
        try:
            if self.capture_method == 'screencapture':
                result = subprocess.run(
                    ['screencapture', '-x', '-t', 'jpg', '-'],
                    capture_output=True
                )
                return result.stdout
            
            elif self.capture_method == 'ffmpeg':
                result = subprocess.run([
                    'ffmpeg', '-f', 'avfoundation', '-i', '1',
                    '-vframes', '1', '-f', 'mjpeg', 'pipe:1'
                ], capture_output=True)
                return result.stdout
            
            elif self.capture_method == 'pyautogui':
                import pyautogui
                screenshot = pyautogui.screenshot()
                buf = io.BytesIO()
                screenshot.save(buf, format='JPEG', quality=70)
                return buf.getvalue()
        
        except Exception as e:
            self.log(f"Capture error: {e}", "ERROR")
            return None
    
    def capture_and_send(self):
        if not self.stream_id:
            return
        
        frame = self.capture_screen()
        if frame:
            self.send_frame(frame, "video")

if __name__ == "__main__":
    agent = MacOSAgent()
    
    print("""
    ╔══════════════════════════════════════╗
    ║   macOS Agent v2.1                   ║
    ║   Capture: CoreGraphics              ║
    ╚══════════════════════════════════════╝
    """)
    
    if agent.init_capture():
        agent.run()
    else:
        print("Install: pip install pyautogui pillow")
