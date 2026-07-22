#!/usr/bin/env python3
# http_signaling.py - HTTP API для Nexus Remote на Render
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import socket
import struct
import threading
import os
import time

peers = {}  # peer_id -> {"status": "online", "ip": "...", "port": ...}
offers = {}  # target -> {"from": ..., "sdp": ...}
relay_connections = {}  # session_id -> {"peer1": ..., "peer2": ...}

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
            self.wfile.write(json.dumps({
                "peers": list(peers.keys()),
                "count": len(peers)
            }).encode())
        elif self.path.startswith('/offer/'):
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
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "running",
                "peers": len(peers),
                "offers": len(offers),
                "sessions": len(relay_connections)
            }).encode())
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
            peer_ip = data.get('ip', self.client_address[0])
            peer_port = data.get('port', 0)
            if peer_id:
                peers[peer_id] = {
                    'status': 'online', 
                    'ip': peer_ip, 
                    'port': peer_port,
                    'last_seen': 'now'
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "registered", 
                    "peer_id": peer_id,
                    "peers": list(peers.keys()),
                    "count": len(peers)
                }).encode())
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
                offers[target] = {
                    'from': from_peer, 
                    'sdp': sdp, 
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "offer_sent", 
                    "to": target,
                    "from": from_peer
                }).encode())
                print(f"Offer from {from_peer} to {target}")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "target and sdp required"}).encode())
        
        elif self.path == '/answer':
            target = data.get('target', '')
            sdp = data.get('sdp', '')
            from_peer = data.get('from', 'unknown')
            if target and sdp:
                answer_key = target + "_answer"
                offers[answer_key] = {
                    'from': from_peer, 
                    'sdp': sdp,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "answer_sent"}).encode())
                print(f"Answer from {from_peer} to {target}")
            else:
                self.send_response(400)
                self.end_headers()
        
        elif self.path == '/connect':
            # ачать relay сессию между двумя пирами
            peer1 = data.get('peer1', '')
            peer2 = data.get('peer2', '')
            if peer1 in peers and peer2 in peers:
                session_id = f"{peer1}_{peer2}_{int(time.time())}"
                relay_connections[session_id] = {
                    'peer1': peer1,
                    'peer2': peer2,
                    'status': 'active',
                    'started': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "connected",
                    "session_id": session_id,
                    "peer1": peer1,
                    "peer2": peer2
                }).encode())
                print(f"Relay session started: {session_id}")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "peer not found"}).encode())
        
        elif self.path == '/relay':
            # тправить данные через relay
            target = data.get('target', '')
            payload = data.get('data', '')
            if target and payload:
                # Сохраняем данные для получателя
                if 'messages' not in peers.get(target, {}):
                    if target not in peers:
                        peers[target] = {}
                    peers[target]['messages'] = []
                peers[target]['messages'].append({
                    'from': data.get('from', 'unknown'),
                    'data': payload,
                    'time': time.strftime('%H:%M:%S')
                })
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "relayed"}).encode())
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "target and data required"}).encode())
        
        elif self.path == '/messages':
            # олучить сообщения для пира
            peer_id = data.get('peer_id', '')
            if peer_id in peers:
                messages = peers[peer_id].get('messages', [])
                peers[peer_id]['messages'] = []  # чищаем
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"messages": messages}).encode())
            else:
                self.send_response(404)
                self.end_headers()
        
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
