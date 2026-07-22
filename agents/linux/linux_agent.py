#!/usr/bin/env python3
# linux_agent.py - Linux агент с захватом экрана
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nexus_agent import NexusAgent
import time
import subprocess
import io

class LinuxAgent(NexusAgent):
    """Linux агент с захватом экрана"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.capture_method = None
        self.display = os.environ.get('DISPLAY', ':0')
    
    def init_capture(self):
        """нициализация захвата"""
        methods = []
        
        # роверяем доступные методы
        if self._check_command('import'):
            methods.append('imagemagick')
        if self._check_command('scrot'):
            methods.append('scrot')
        if self._check_command('ffmpeg'):
            methods.append('ffmpeg')
        
        # робуем PIL
        try:
            from PIL import ImageGrab
            methods.append('PIL')
        except:
            pass
        
        # робуем pyautogui
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
            self.log("No capture method available! Install: scrot, imagemagick, or PIL", "ERROR")
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
            if self.capture_method == 'imagemagick':
                result = subprocess.run(
                    ['import', '-window', 'root', '-quality', '70', 'jpeg:-'],
                    capture_output=True,
                    env={**os.environ, 'DISPLAY': self.display}
                )
                return result.stdout
            
            elif self.capture_method == 'scrot':
                result = subprocess.run(
                    ['scrot', '-', '-q', '70'],
                    capture_output=True
                )
                return result.stdout
            
            elif self.capture_method == 'ffmpeg':
                result = subprocess.run([
                    'ffmpeg', '-f', 'x11grab', '-video_size', '1920x1080',
                    '-i', self.display, '-vframes', '1', '-f', 'mjpeg',
                    '-q:v', '10', 'pipe:1'
                ], capture_output=True)
                return result.stdout
            
            elif self.capture_method in ('PIL', 'pyautogui'):
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
    agent = LinuxAgent()
    
    print("""
    ╔══════════════════════════════════════╗
    ║   Linux Agent v2.1                   ║
    ║   Capture: X11/Wayland               ║
    ╚══════════════════════════════════════╝
    """)
    
    if agent.init_capture():
        agent.run()
    else:
        print("Install: sudo apt install scrot imagemagick ffmpeg")
        print("Or: pip install pyautogui pillow")
