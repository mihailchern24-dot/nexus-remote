#!/usr/bin/env python3
# http_signaling.py - Nexus Remote Server v2.0
# оддержка: Windows, Linux, macOS, Android, iOS, PlayStation, Xbox, Nintendo, Android TV, Android Auto
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
import os
import base64
from codec_config import get_codec_config, get_quality_preset

peers = {}       # peer_id -> {platform, ip, port, codec, status}
offers = {}      # target -> {from, sdp, codec_config}
sessions = {}    # session_id -> {peer1, peer2, codec, quality}
messages = {}    # peer_id -> [{from, data, type, time}]
streams = {}     # stream_id -> {source, target, codec, bitrate, fps, resolution}

class NexusHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('X-Nexus-Server', 'v2.0')
        self.end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/' or self.path == '/health':
            self._json_response({"status": "ok", "server": "Nexus Remote v2.0"})
        
        elif self.path == '/peers':
            self._json_response({
                "peers": {pid: {"platform": p.get("platform"), "status": p.get("status")} 
                         for pid, p in peers.items()},
                "count": len(peers)
            })
        
        elif self.path.startswith('/offer/'):
            target = self.path.split('/')[-1]
            offer = offers.get(target)
            if offer:
                self._json_response(offer)
            else:
                self._json_error(404, "no_offer")
        
        elif self.path == '/streams':
            self._json_response({
                "streams": list(streams.values()),
                "count": len(streams)
            })
        
        elif self.path == '/status':
            self._json_response({
                "status": "running",
                "peers": len(peers),
                "offers": len(offers),
                "sessions": len(sessions),
                "streams": len(streams),
                "platforms": self._count_platforms()
            })
        
        elif self.path == '/codecs':
            platform = self.headers.get('X-Platform', 'linux')
            self._json_response(get_codec_config(platform))
        
        else:
            self._json_error(404, "not_found")
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
        
        try:
            data = json.loads(body)
        except:
            data = {}
        
        client_ip = self.headers.get('X-Forwarded-For', self.client_address[0])
        
        if self.path == '/register':
            peer_id = data.get('peer_id', '')
            platform = data.get('platform', 'unknown')
            codec = data.get('codec', 'auto')
            resolution = data.get('resolution', '1080p')
            fps = data.get('fps', 30)
            
            if peer_id:
                peers[peer_id] = {
                    'platform': platform,
                    'ip': client_ip,
                    'port': data.get('port', 0),
                    'codec': codec,
                    'resolution': resolution,
                    'fps': fps,
                    'status': 'online',
                    'registered_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'last_seen': time.time()
                }
                
                # вто-выбор кодека для платформы
                codec_config = get_codec_config(platform)
                
                self._json_response({
                    "status": "registered",
                    "peer_id": peer_id,
                    "platform": platform,
                    "codec_config": codec_config,
                    "peers": list(peers.keys()),
                    "count": len(peers)
                })
                print(f"[+] {peer_id} ({platform}) registered. Total: {len(peers)}")
            else:
                self._json_error(400, "peer_id required")
        
        elif self.path == '/start_stream':
            # ачать стриминг экрана
            source = data.get('source', '')
            target = data.get('target', '')
            quality = data.get('quality', 'auto')
            
            if source in peers and target in peers:
                stream_id = f"stream_{source}_{target}_{int(time.time())}"
                quality_config = get_quality_preset(quality)
                
                streams[stream_id] = {
                    'id': stream_id,
                    'source': source,
                    'target': target,
                    'codec': data.get('codec', 'h264'),
                    'bitrate': quality_config['bitrate'],
                    'fps': quality_config['fps'],
                    'resolution': quality_config['resolution'],
                    'started_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'active',
                    'frames_sent': 0
                }
                
                self._json_response({
                    "status": "streaming",
                    "stream_id": stream_id,
                    "config": quality_config
                })
                print(f"[STREAM] {source} -> {target} ({quality_config['resolution']} @ {quality_config['fps']}fps)")
            else:
                self._json_error(404, "peer not found")
        
        elif self.path == '/send_frame':
            # тправить кадр видео
            stream_id = data.get('stream_id', '')
            frame_data = data.get('frame', '')  # base64 encoded
            frame_type = data.get('type', 'video')  # video/audio/input
            target = data.get('target', '')
            
            if target and frame_data:
                if target not in messages:
                    messages[target] = []
                
                messages[target].append({
                    'from': data.get('from', 'unknown'),
                    'type': frame_type,
                    'data': frame_data,
                    'size': len(frame_data),
                    'timestamp': time.time(),
                    'stream_id': stream_id
                })
                
                # бновляем счетчик кадров
                if stream_id in streams:
                    streams[stream_id]['frames_sent'] += 1
                
                self._json_response({"status": "sent", "size": len(frame_data)})
            else:
                self._json_error(400, "stream_id and frame required")
        
        elif self.path == '/get_frame':
            # олучить кадр для отображения
            peer_id = data.get('peer_id', '')
            stream_id = data.get('stream_id', '')
            
            if peer_id in messages and messages[peer_id]:
                frame = messages[peer_id].pop(0)
                self._json_response(frame)
            else:
                self._json_response({"type": "empty"})
        
        elif self.path == '/stop_stream':
            stream_id = data.get('stream_id', '')
            if stream_id in streams:
                streams[stream_id]['status'] = 'stopped'
                streams[stream_id]['stopped_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
                self._json_response({"status": "stopped", "stream_id": stream_id})
            else:
                self._json_error(404, "stream not found")
        
        elif self.path == '/ping':
            peer_id = data.get('peer_id', '')
            if peer_id in peers:
                peers[peer_id]['last_seen'] = time.time()
                self._json_response({"status": "pong"})
            else:
                self._json_error(404, "peer not found")
        
        else:
            self._json_error(404, "not_found")
    
    def _json_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _json_error(self, code, message):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())
    
    def _count_platforms(self):
        platforms = {}
        for p in peers.values():
            plat = p.get('platform', 'unknown')
            platforms[plat] = platforms.get(plat, 0) + 1
        return platforms
    
    def log_message(self, format, *args):
        pass

port = int(os.environ.get('PORT', 10000))
print(f"""
╔══════════════════════════════════════════════╗
║     Nexus Remote Server v2.0                 ║
║     Port: {port}                              ║
║     Platforms: All                           ║
╚══════════════════════════════════════════════╝
""")
HTTPServer(('0.0.0.0', port), NexusHandler).serve_forever()
