#!/usr/bin/env python3
# http_signaling.py - HTTP API для сигналинга Render
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys
import os

peers = {}
offers = {}

class SignalingHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
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
        elif self.path.startswith('/offer/'):
            # GET /offer/peer_id - получить offer для пира
            target = self.path.split('/')[-1]
            if target in offers:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(offers[target]).encode())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "no_offer"}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
        
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}
        
        if self.path == '/register':
            peer_id = data.get('peer_id', '')
            if peer_id:
                peers[peer_id] = {'status': 'online', 'last_seen': 'now'}
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "registered", "peer_id": peer_id}).encode())
                print(f"Peer registered: {peer_id} (total: {len(peers)})")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "peer_id required"}).encode())
        
        elif self.path == '/offer':
            target = data.get('target', '')
            sdp = data.get('sdp', '')
            from_peer = data.get('from', 'unknown')
            if target and sdp:
                offers[target] = {'from': from_peer, 'sdp': sdp, 'timestamp': 'now'}
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "offer_sent", "to": target}).encode())
                print(f"Offer from {from_peer} to {target}")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "target and sdp required"}).encode())
        
        elif self.path == '/unregister':
            peer_id = data.get('peer_id', '')
            if peer_id in peers:
                del peers[peer_id]
                print(f"Peer unregistered: {peer_id}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "unregistered"}).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "not_found"}).encode())
    
    def log_message(self, format, *args):
        pass

port = int(os.environ.get('PORT', 10000))
print(f"Nexus HTTP Signaling server on port {port}")
HTTPServer(('0.0.0.0', port), SignalingHandler).serve_forever()
