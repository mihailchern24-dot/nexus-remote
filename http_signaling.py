#!/usr/bin/env python3
# http_signaling.py - HTTP API для сигналинга
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys
import os

peers = {}

class SignalingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        elif self.path == '/peers':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(list(peers.keys())).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length).decode()
        data = json.loads(body)
        
        if self.path == '/register':
            peer_id = data.get('peer_id')
            peers[peer_id] = True
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "registered", "peer_id": peer_id}).encode())
        
        elif self.path == '/offer':
            target = data.get('target')
            sdp = data.get('sdp')
            # В реальном приложении - отправляем offer
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "offer_sent"}).encode())
        
        else:
            self.send_response(404)
            self.end_headers()

port = int(os.environ.get('PORT', 10000))
print(f"HTTP Signaling server on port {port}")
HTTPServer(('0.0.0.0', port), SignalingHandler).serve_forever()
