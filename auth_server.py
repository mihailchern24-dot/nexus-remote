#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# auth_server.py - Nexus Remote Full Auth Server
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, os, time, hashlib, secrets, sqlite3
from datetime import datetime

DB_FILE = "/app/nexus_auth.db" if os.path.exists("/app") else "nexus_auth.db"

class AuthDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = self.conn.cursor()
        c.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                password_hash TEXT,
                token TEXT,
                peer_id TEXT,
                created TEXT,
                last_login TEXT
            );
        ''')
        self.conn.commit()
    
    def register(self, email, password):
        try:
            token = secrets.token_hex(32)
            peer_id = f"nexus-{hashlib.md5(email.encode()).hexdigest()[:12]}"
            pw_hash = hashlib.sha256(password.encode()).hexdigest()
            now = datetime.now().isoformat()
            c = self.conn.cursor()
            c.execute('INSERT INTO users (email, password_hash, token, peer_id, created, last_login) VALUES (?,?,?,?,?,?)',
                     (email, pw_hash, token, peer_id, now, now))
            self.conn.commit()
            return {"status": "registered", "token": token, "peer_id": peer_id}
        except sqlite3.IntegrityError:
            return {"error": "Email already registered"}
    
    def login(self, email, password):
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        c = self.conn.cursor()
        c.execute('SELECT token, peer_id FROM users WHERE email=? AND password_hash=?', (email, pw_hash))
        row = c.fetchone()
        if row:
            c.execute('UPDATE users SET last_login=? WHERE email=?', (datetime.now().isoformat(), email))
            self.conn.commit()
            return {"status": "ok", "token": row[0], "peer_id": row[1]}
        return {"error": "Invalid email or password"}
    
    def reset_password(self, email, new_password):
        pw_hash = hashlib.sha256(new_password.encode()).hexdigest()
        c = self.conn.cursor()
        c.execute('UPDATE users SET password_hash=? WHERE email=?', (pw_hash, email))
        self.conn.commit()
        return c.rowcount > 0

db = AuthDB()

class AuthHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        pages = {
            '/': 'index.html',
            '/login': 'login.html',
            '/register': 'register.html',
            '/reset': 'reset.html',
            '/dashboard': 'dashboard.html',
            '/download': 'download.html',
            '/viewer': 'viewer.html',
            '/speedtest': 'speedtest.html',
            '/status': 'status.html',
            '/docs': 'docs.html',
            '/blog': 'blog.html',
            '/support': 'support.html',
            '/forum': 'forum.html',
            '/wake': 'wake_stream.html',
        }
        
        if self.path in pages:
            self.serve_html(pages[self.path])
        elif self.path == '/api/status':
            self.json_response({"status": "running", "server": "Nexus Remote v4.0"})
        else:
            self.json_response({"error": "Not found"}, 404)
    
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode() if length > 0 else '{}'
        try:
            data = json.loads(body)
        except:
            data = {}
        
        if self.path == '/api/auth/register':
            result = db.register(data.get('email', ''), data.get('password', ''))
            self.json_response(result)
        elif self.path == '/api/auth/login':
            result = db.login(data.get('email', ''), data.get('password', ''))
            self.json_response(result)
        elif self.path == '/api/auth/reset':
            ok = db.reset_password(data.get('email', ''), data.get('new_password', ''))
            if ok:
                self.json_response({"status": "password_reset"})
            else:
                self.json_response({"error": "Email not found"}, 400)
        else:
            self.json_response({"error": "Not found"}, 404)
    
    def serve_html(self, filename):
        path = os.path.join('/app/webapp', filename)
        if not os.path.exists(path):
            path = os.path.join('webapp', filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                html = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode())
        except Exception as e:
            self.json_response({"error": str(e)}, 500)
    
    def json_response(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"Nexus Remote Auth Server on port {port}")
    HTTPServer(('0.0.0.0', port), AuthHandler).serve_forever()

