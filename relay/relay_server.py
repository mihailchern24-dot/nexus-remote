#!/usr/bin/env python3
# relay_server.py - етранслятор для P2P обхода
import socket
import threading
import json

class RelayServer:
    def __init__(self, port=9000):
        self.port = port
        self.peers = {}
    
    def start(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('0.0.0.0', self.port))
        sock.listen(50)
        print(f"Relay server on port {self.port}")
        
        while True:
            conn, addr = sock.accept()
            threading.Thread(target=self.handle_peer, args=(conn, addr)).start()
    
    def handle_peer(self, conn, addr):
        # бработка подключения
        pass

if __name__ == "__main__":
    RelayServer().start()
