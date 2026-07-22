# Android Agent (Termux)
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from nexus_client_base import NexusBaseClient, Platform

class AndroidAgent(NexusBaseClient):
    def __init__(self):
        super().__init__(Platform.ANDROID.value)
    
    def capture_screen(self):
        import subprocess
        return subprocess.run(['screencap', '-p'], capture_output=True).stdout

if __name__ == "__main__":
    agent = AndroidAgent()
    agent.register()
    print(f"Android Agent: {agent.peer_id}")
