#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# auth_server.py - Nexus Remote Auth Backend
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, os, time, hashlib, secrets, sqlite3
from datetime import datetime
from urllib.parse import parse_qs, urlparse

DB_FILE = "nexus_auth.db"

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
                reset_token TEXT,
                created TEXT,
                last_login TEXT
            );
            CREATE TABLE IF NOT EXISTS oauth (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                provider TEXT,
                provider_id TEXT
            );
        ''')
        self.conn.commit()
    
    def register(self, email, password):
        try:
            token = secrets.token_hex(32)
            peer_id = f"user-{hashlib.md5(email.encode()).hexdigest()[:12]}"
            pw_hash = hashlib.sha256(password.encode()).hexdigest()
            c = self.conn.cursor()
            c.execute('INSERT INTO users (email, password_hash, token, peer_id, created) VALUES (?,?,?,?,?)',
                     (email, pw_hash, token, peer_id, datetime.now().isoformat()))
            self.conn.commit()
            return {"status": "registered", "token": token, "peer_id": peer_id}
        except sqlite3.IntegrityError:
            return {"error": "Email already exists"}
    
    def login(self, email, password):
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        c = self.conn.cursor()
        c.execute('SELECT token, peer_id FROM users WHERE email=? AND password_hash=?', (email, pw_hash))
        row = c.fetchone()
        if row:
            c.execute('UPDATE users SET last_login=? WHERE email=?', (datetime.now().isoformat(), email))
            self.conn.commit()
            return {"status": "ok", "token": row[0], "peer_id": row[1]}
        return {"error": "Invalid credentials"}
    
    def reset_password(self, email, new_password):
        pw_hash = hashlib.sha256(new_password.encode()).hexdigest()
        c = self.conn.cursor()
        c.execute('UPDATE users SET password_hash=? WHERE email=?', (pw_hash, email))
        self.conn.commit()
        return c.rowcount > 0
    
    def verify_token(self, token):
        c = self.conn.cursor()
        c.execute('SELECT email, peer_id FROM users WHERE token=?', (token,))
        return c.fetchone()

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
        if self.path == '/':
            self._serve_html('/app/webapp/index.html')
        elif self.path == '/login':
            self._serve_html('/app/webapp/index.html')
        elif self.path == '/register':
            self._serve_html('/app/webapp/register.html')
        elif self.path == '/reset':
            self._serve_html('/app/webapp/reset.html')
        elif self.path == '/api/status':
            self._json({"status": "running", "users": "online"})
        else:
            self._json_error(404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
        try:
            data = json.loads(body)
        except:
            data = {}
        
        if self.path == '/api/auth/login':
            result = db.login(data.get('email', ''), data.get('password', ''))
            self._json(result)
        
        elif self.path == '/api/auth/register':
            result = db.register(data.get('email', ''), data.get('password', ''))
            self._json(result)
        
        elif self.path == '/api/auth/reset':
            email = data.get('email', '')
            new_pass = data.get('new_password', '')
            if db.reset_password(email, new_pass):
                self._json({"status": "password_reset"})
            else:
                self._json_error(400, "Email not found")
        
        elif self.path == '/api/auth/verify':
            user = db.verify_token(data.get('token', ''))
            if user:
                self._json({"status": "valid", "email": user[0], "peer_id": user[1]})
            else:
                self._json_error(401, "Invalid token")
        
        elif self.path == '/api/auth/oauth':
            provider = data.get('provider', '')
            self._json({"status": "oauth_redirect", "provider": provider, "url": f"/oauth/{provider}"})
        
        else:
            self._json_error(404)
    
    def _serve_html(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                html = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode())
        except:
            self._json_error(404)
    
    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _json_error(self, code, msg=""):
        self._json({"error": msg or "Error"}, code)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"Auth server on port {port}")
    HTTPServer(('0.0.0.0', port), AuthHandler).serve_forever()

