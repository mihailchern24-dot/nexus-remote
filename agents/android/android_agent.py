#!/usr/bin/env python3
# android_agent.py - Android агент (Termux)
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nexus_agent import NexusAgent
import subprocess
import time

class AndroidAgent(NexusAgent):
    """Android агент для Termux"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.platform = "android"
    
    def init_capture(self):
        """нициализация захвата"""
        # а Android используем screencap
        if self._check_command('screencap'):
            self.capture_method = 'screencap'
            self.log("Capture: Android screencap")
            return True
        else:
            self.log("screencap not found! Run in Termux with Android SDK", "ERROR")
            return False
    
    def _check_command(self, cmd):
        try:
            subprocess.run(['which', cmd], capture_output=True, check=True)
            return True
        except:
            return False
    
    def capture_screen(self):
        """ахват экрана Android"""
        try:
            # спользуем screencap
            result = subprocess.run(
                ['screencap', '-p'],
                capture_output=True
            )
            return result.stdout
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
    agent = AndroidAgent()
    
    print("""
    ╔══════════════════════════════════════╗
    ║   Android Agent v2.1 (Termux)        ║
    ║   Capture: screencap                 ║
    ╚══════════════════════════════════════╝
    """)
    
    if agent.init_capture():
        agent.run()
    else:
        print("Run in Termux: pkg install android-tools")
