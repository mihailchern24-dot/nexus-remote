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
        c.execute('SELECT token, peer_id, created FROM users WHERE email=? AND password_hash=?', (email, pw_hash))
        row = c.fetchone()
        if row:
            c.execute('UPDATE users SET last_login=? WHERE email=?', (datetime.now().isoformat(), email))
            self.conn.commit()
            return {"status": "ok", "token": row[0], "peer_id": row[1], "created": row[2]}
        return {"error": "Invalid email or password"}
    
    def reset_password(self, email, new_password):
        pw_hash = hashlib.sha256(new_password.encode()).hexdigest()
        c = self.conn.cursor()
        c.execute('UPDATE users SET password_hash=? WHERE email=?', (pw_hash, email))
        self.conn.commit()
        return c.rowcount > 0
    
    def get_user(self, token):
        c = self.conn.cursor()
        c.execute('SELECT email, peer_id, created, last_login FROM users WHERE token=?', (token,))
        row = c.fetchone()
        if row:
            return {"email": row[0], "peer_id": row[1], "created": row[2], "last_login": row[3]}
        return None

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
                routes = {
            '/': '/app/webapp/index.html',
            '/login': '/app/webapp/login.html',
            '/register': '/app/webapp/register.html',
            '/reset': '/app/webapp/reset.html',
            '/dashboard': '/app/webapp/dashboard.html',
            '/download': '/app/webapp/download.html',
            '/viewer': '/app/webapp/viewer.html',
            '/speedtest': '/app/webapp/speedtest.html',
            '/status': '/app/webapp/status.html',
            '/docs': '/app/webapp/docs.html',
            '/blog': '/app/webapp/blog.html',
            '/support': '/app/webapp/support.html',
            '/forum': '/app/webapp/forum.html',
        }
        
        if self.path in routes:
            self._serve_html(routes[self.path])
        elif self.path == '/api/user':
            self._handle_get_user()
        elif self.path == '/api/status':
            self._json({"status": "running", "server": "Nexus Remote v4.0"})
        else:
            # Try to serve static files
            path = '/app/webapp' + self.path
            if os.path.exists(path):
                self._serve_html(path)
            else:
                self._json_error(404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
        try:
            data = json.loads(body)
        except:
            data = {}
        
                routes = {
            '/': '/app/webapp/index.html',
            '/login': '/app/webapp/login.html',
            '/register': '/app/webapp/register.html',
            '/reset': '/app/webapp/reset.html',
            '/dashboard': '/app/webapp/dashboard.html',
            '/download': '/app/webapp/download.html',
            '/viewer': '/app/webapp/viewer.html',
            '/speedtest': '/app/webapp/speedtest.html',
            '/status': '/app/webapp/status.html',
            '/docs': '/app/webapp/docs.html',
            '/blog': '/app/webapp/blog.html',
            '/support': '/app/webapp/support.html',
            '/forum': '/app/webapp/forum.html',
        }
        
        if self.path in routes:
            result = routes[self.path]()
            self._json(result)
        elif self.path == '/api/auth/reset':
            email = data.get('email', '')
            new_pass = data.get('new_password', '')
            if db.reset_password(email, new_pass):
                self._json({"status": "password_reset"})
            else:
                self._json_error(400, "Email not found")
        else:
            self._json_error(404)
    
    def _handle_get_user(self):
        token = self.headers.get('Authorization', '').replace('Bearer ', '')
        if token:
            user = db.get_user(token)
            if user:
                self._json(user)
                return
        self._json_error(401, "Invalid token")
    
    def _serve_html(self, path):
        try:
            # Try /app path first (Docker), then local
            if not os.path.exists(path):
                path = path.replace('/app/', '')
            
            with open(path, 'r', encoding='utf-8') as f:
                html = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode())
        except Exception as e:
            self._json_error(404, str(e))
    
    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _json_error(self, code, msg="Error"):
        self._json({"error": msg}, code)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"Nexus Remote Auth Server on port {port}")
    HTTPServer(('0.0.0.0', port), AuthHandler).serve_forever()

