# Windows Agent
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from nexus_client_base import NexusBaseClient, Platform
import pyautogui, io, time, threading

class WindowsAgent(NexusBaseClient):
    def __init__(self):
        super().__init__(Platform.WINDOWS.value)
    
    def start_capture(self, peer_id):
        def loop():
            while peer_id in self.connected_peers:
                ss = pyautogui.screenshot()
                buf = io.BytesIO()
                ss.save(buf, format='JPEG', quality=50)
                self.send_frame(buf.getvalue())
                time.sleep(1/30)
        threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    agent = WindowsAgent()
    agent.register()
    print(f"Windows Agent: {agent.peer_id}")
