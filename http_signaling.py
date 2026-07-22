#!/usr/bin/env python3
# http_signaling.py - Nexus Remote Server v2.0 с сжатием и шифрованием
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
import os
import base64
from compression import AdaptiveCompressor, CompressionMethod
from encryption import NexusCrypto, EncryptionMethod
from codec_config import get_codec_config, get_quality_preset

peers = {}
streams = {}
messages = {}
crypto = NexusCrypto()

class NexusHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self._cors_headers()
        self.send_response(200)
        self.end_headers()
    
    def do_OPTIONS(self):
        self._cors_headers()
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/':
            self._json({"server": "Nexus Remote v2.0", "features": ["compression", "encryption"]})
        elif self.path == '/status':
            self._json({
                "status": "running",
                "peers": len(peers),
                "streams": len(streams),
                "compression_methods": [m.value for m in CompressionMethod],
                "encryption_methods": [m.value for m in EncryptionMethod]
            })
        elif self.path == '/methods':
            self._json({
                "compression": [m.value for m in CompressionMethod],
                "encryption": [m.value for m in EncryptionMethod]
            })
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
            self._handle_register(data)
        elif self.path == '/start_stream':
            self._handle_stream_start(data)
        elif self.path == '/send_frame':
            self._handle_send_frame(data)
        elif self.path == '/get_frame':
            self._handle_get_frame(data)
        else:
            self._json_error(404)
    
    def _handle_register(self, data):
        peer_id = data.get('peer_id', '')
        if peer_id:
            peers[peer_id] = {
                'platform': data.get('platform', 'unknown'),
                'compression': data.get('compression', 'zlib'),
                'encryption': data.get('encryption', 'aes_gcm'),
                'status': 'online',
                'registered_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            self._json({
                "status": "registered",
                "peer_id": peer_id,
                "supported_methods": {
                    "compression": [m.value for m in CompressionMethod],
                    "encryption": [m.value for m in EncryptionMethod]
                }
            })
    
    def _handle_stream_start(self, data):
        source = data.get('source', '')
        target = data.get('target', '')
        compression = data.get('compression', 'zlib')
        encryption = data.get('encryption', 'aes_gcm')
        quality = data.get('quality', 'high')
        
        if source in peers and target in peers:
            stream_id = f"stream_{source}_{target}_{int(time.time())}"
            quality_config = get_quality_preset(quality)
            
            streams[stream_id] = {
                'id': stream_id,
                'source': source,
                'target': target,
                'compression': compression,
                'encryption': encryption,
                'quality': quality_config,
                'status': 'active',
                'frames_sent': 0,
                'bytes_sent': 0,
                'bytes_saved': 0
            }
            
            self._json({
                "status": "streaming",
                "stream_id": stream_id,
                "compression": compression,
                "encryption": encryption,
                "quality": quality_config
            })
    
    def _handle_send_frame(self, data):
        stream_id = data.get('stream_id', '')
        frame_data = data.get('frame', '')
        target = data.get('target', '')
        compression = data.get('compression', 'zlib')
        encryption = data.get('encryption', 'aes_gcm')
        
        if target and frame_data:
            # екодируем base64
            raw_data = base64.b64decode(frame_data)
            original_size = len(raw_data)
            
            # Сжимаем
            compressed, comp_method, ratio = AdaptiveCompressor.best_compress(raw_data)
            compressed_size = len(compressed)
            
            # Шифруем
            encrypted, enc_method, meta = crypto.encrypt(compressed, 
                EncryptionMethod(encryption) if encryption != 'auto' else EncryptionMethod.AES_GCM)
            encrypted_size = len(encrypted)
            
            # одируем обратно в base64
            final_data = base64.b64encode(encrypted).decode()
            
            if target not in messages:
                messages[target] = []
            
            messages[target].append({
                'from': data.get('from', 'unknown'),
                'type': 'video',
                'data': final_data,
                'compression': comp_method.value,
                'encryption': enc_method.value,
                'metadata': meta,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'encrypted_size': encrypted_size,
                'timestamp': time.time(),
                'stream_id': stream_id
            })
            
            if stream_id in streams:
                streams[stream_id]['frames_sent'] += 1
                streams[stream_id]['bytes_sent'] += original_size
                streams[stream_id]['bytes_saved'] += (original_size - encrypted_size)
            
            self._json({
                "status": "sent",
                "original": original_size,
                "compressed": compressed_size,
                "encrypted": encrypted_size,
                "compression_ratio": f"{ratio:.1f}%",
                "total_saved": f"{(original_size - encrypted_size) / original_size * 100:.1f}%"
            })
    
    def _handle_get_frame(self, data):
        peer_id = data.get('peer_id', '')
        if peer_id in messages and messages[peer_id]:
            frame = messages[peer_id].pop(0)
            
            # екодируем
            encrypted = base64.b64decode(frame['data'])
            
            # асшифровываем
            decrypted = crypto.decrypt(encrypted, 
                EncryptionMethod(frame['encryption']), 
                frame.get('metadata', {}))
            
            # аспаковываем
            decompressed = AdaptiveCompressor.decompress(decrypted,
                CompressionMethod(frame['compression']))
            
            # озвращаем оригинал
            frame['data'] = base64.b64encode(decompressed).decode()
            self._json(frame)
        else:
            self._json({"type": "empty"})
    
    def _json(self, data):
        self._cors_headers()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _json_error(self, code):
        self._cors_headers()
        self.send_response(code)
        self.end_headers()
    
    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def log_message(self, format, *args):
        pass

port = int(os.environ.get('PORT', 10000))
print(f"Nexus Remote v2.0 with Compression & Encryption on port {port}")
HTTPServer(('0.0.0.0', port), NexusHandler).serve_forever()
