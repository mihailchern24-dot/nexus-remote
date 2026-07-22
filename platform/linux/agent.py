# Linux Agent
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from nexus_client_base import NexusBaseClient, Platform
import subprocess, time, threading

class LinuxAgent(NexusBaseClient):
    def __init__(self):
        super().__init__(Platform.LINUX.value)
    
    def capture_screen(self):
        result = subprocess.run(['import', '-window', 'root', 'jpeg:-'], capture_output=True)
        return result.stdout

if __name__ == "__main__":
    agent = LinuxAgent()
    agent.register()
    print(f"Linux Agent: {agent.peer_id}")
