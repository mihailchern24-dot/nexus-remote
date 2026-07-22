#!/usr/bin/env python3
# http_signaling.py - HTTP API для сигналинга Render
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys
import os

peers = {}

class SignalingHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        """Health check support"""
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/' or self.path == '/health':
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
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length).decode()
            try:
                data = json.loads(body)
            except:
                data = {}
        else:
            data = {}
        
        if self.path == '/register':
            peer_id = data.get('peer_id', 'unknown')
            peers[peer_id] = True
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "registered", "peer_id": peer_id}).encode())
            print(f"Peer registered: {peer_id}")
        
        elif self.path == '/offer':
            target = data.get('target')
            sdp = data.get('sdp')
            print(f"Offer to {target}: {sdp[:50]}...")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "offer_sent"}).encode())
        
        elif self.path == '/list':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(list(peers.keys())).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "not_found"}).encode())
    
    def log_message(self, format, *args):
        # Тихий режим
        pass

port = int(os.environ.get('PORT', 10000))
print(f"HTTP Signaling server on port {port}")
HTTPServer(('0.0.0.0', port), SignalingHandler).serve_forever()
