#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# http_signaling.py - Nexus Remote Server v2.1
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
import os
import base64
import socket
import struct
from compression import AdaptiveCompressor, CompressionMethod
from encryption import NexusCrypto, EncryptionMethod

peers = {}
streams = {}
messages = {}
crypto = NexusCrypto()

CODEC_CONFIGS = {
    "windows": {"primary": "h264_nvenc", "fallback": "h264_mf", "software": "libx264"},
    "linux": {"primary": "h264_vaapi", "software": "libx264"},
    "macos": {"primary": "h264_videotoolbox", "software": "libx264"},
    "android": {"primary": "h264_mediacodec", "software": "libx264"},
    "ios": {"primary": "h264_videotoolbox", "software": "libx264"},
}

QUALITY_PRESETS = {
    "ultra": {"bitrate": 50000, "fps": 60, "resolution": "4K"},
    "high": {"bitrate": 25000, "fps": 60, "resolution": "1080p"},
    "medium": {"bitrate": 10000, "fps": 30, "resolution": "720p"},
    "low": {"bitrate": 5000, "fps": 24, "resolution": "480p"},
    "minimal": {"bitrate": 2000, "fps": 15, "resolution": "360p"}
}

def send_wol_packet(mac_address):
    try:
        mac = mac_address.replace(':', '').replace('-', '').replace(' ', '')
        if len(mac) != 12:
            return False
        data = bytes.fromhex('FF' * 6 + mac * 16)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(data, ('255.255.255.255', 9))
        sock.close()
        return True
    except:
        return False

class NexusHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/' or self.path == '/health':
            self._json({"status": "ok", "server": "Nexus Remote v2.1"})
        elif self.path == '/status':
            self._json({
                "status": "running",
                "peers": len(peers),
                "streams": len(streams),
                "compression": [m.value for m in CompressionMethod],
                "encryption": [m.value for m in EncryptionMethod]
            })
        elif self.path == '/methods':
            self._json({
                "compression": [m.value for m in CompressionMethod],
                "encryption": [m.value for m in EncryptionMethod],
                "platforms": list(CODEC_CONFIGS.keys())
            })
        elif self.path == '/peers':
            self._json({"peers": list(peers.keys()), "count": len(peers)})
        else:
            self._json_error(404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
        
        try:
            data = json.loads(body)
        except:
            data = {}
        
        if self.path == '/register':
            peer_id = data.get('peer_id', '')
            if peer_id:
                peers[peer_id] = {
                    'platform': data.get('platform', 'unknown'),
                    'codec': CODEC_CONFIGS.get(data.get('platform', 'linux'), {}),
                    'compression': data.get('compression', 'zlib'),
                    'encryption': data.get('encryption', 'aes_gcm'),
                    'status': 'online'
                }
                self._json({
                    "status": "registered",
                    "peer_id": peer_id,
                    "codec_config": CODEC_CONFIGS.get(data.get('platform', 'linux'), {}),
                    "compression_methods": [m.value for m in CompressionMethod],
                    "encryption_methods": [m.value for m in EncryptionMethod]
                })
            else:
                self._json_error(400)
        
        elif self.path == '/start_stream':
            source = data.get('source', '')
            target = data.get('target', '')
            quality = data.get('quality', 'high')
            
            if source in peers and target in peers:
                stream_id = f"stream_{source}_{target}_{int(time.time())}"
                quality_config = QUALITY_PRESETS.get(quality, QUALITY_PRESETS['high'])
                
                streams[stream_id] = {
                    'id': stream_id, 'source': source, 'target': target,
                    'compression': data.get('compression', 'zlib'),
                    'encryption': data.get('encryption', 'aes_gcm'),
                    'quality': quality_config, 'status': 'active', 'frames_sent': 0
                }
                
                self._json({
                    "status": "streaming", "stream_id": stream_id,
                    "quality": quality_config,
                    "compression": data.get('compression', 'zlib'),
                    "encryption": data.get('encryption', 'aes_gcm')
                })
            else:
                self._json_error(404)
        
        elif self.path == '/send_frame':
            stream_id = data.get('stream_id', '')
            frame_data = data.get('frame', '')
            target = data.get('target', '')
            
            if target and frame_data:
                raw_data = base64.b64decode(frame_data) if isinstance(frame_data, str) else frame_data
                original_size = len(raw_data)
                
                compressed, comp_method, ratio = AdaptiveCompressor.best_compress(raw_data)
                encrypted, enc_method, meta = crypto.encrypt(compressed)
                final_data = base64.b64encode(encrypted).decode()
                
                if target not in messages:
                    messages[target] = []
                
                messages[target].append({
                    'from': data.get('from', 'unknown'), 'type': 'video',
                    'data': final_data, 'compression': comp_method.value,
                    'encryption': enc_method.value, 'metadata': meta,
                    'original_size': original_size, 'compressed_size': len(compressed),
                    'encrypted_size': len(encrypted), 'timestamp': time.time(),
                    'stream_id': stream_id
                })
                
                if stream_id in streams:
                    streams[stream_id]['frames_sent'] += 1
                
                self._json({
                    "status": "sent",
                    "compression_ratio": f"{ratio:.1f}%",
                    "total_saved": f"{(original_size - len(encrypted)) / original_size * 100:.1f}%"
                })
            else:
                self._json_error(400)
        
        elif self.path == '/get_frame':
            peer_id = data.get('peer_id', '')
            if peer_id in messages and messages[peer_id]:
                frame = messages[peer_id].pop(0)
                encrypted = base64.b64decode(frame['data'])
                decrypted = crypto.decrypt(encrypted, frame['encryption'], frame.get('metadata', {}))
                decompressed = AdaptiveCompressor.decompress(decrypted, CompressionMethod(frame['compression']))
                frame['data'] = base64.b64encode(decompressed).decode()
                self._json(frame)
            else:
                self._json({"type": "empty"})
        
        elif self.path == '/stop_stream':
            stream_id = data.get('stream_id', '')
            if stream_id in streams:
                streams[stream_id]['status'] = 'stopped'
                self._json({"status": "stopped"})
            else:
                self._json_error(404)
        
        elif self.path == '/wol':
            mac = data.get('mac', '')
            if mac:
                success = send_wol_packet(mac)
                self._json({"status": "wol_sent", "success": success, "mac": mac})
            else:
                self._json_error(400)
        
        else:
            self._json_error(404)
    
    def _json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _json_error(self, code):
        self.send_response(code)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
    
    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"Nexus Remote v2.1 on port {port}")
    HTTPServer(('0.0.0.0', port), NexusHandler).serve_forever()
