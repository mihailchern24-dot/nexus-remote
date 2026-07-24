#!/usr/bin/env python3
import json, os, time, hashlib, secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

DATA_FILE = "/app/nexus_data.json" if os.path.exists("/app") else "nexus_data.json"

def load():
    try:
        with open(DATA_FILE) as f: return json.load(f)
    except: return {"users":{}, "peers":{}, "streams":{}}

def save(d):
    with open(DATA_FILE,"w") as f: json.dump(d, f, indent=2)

data = load()
if not data.get("users"): data["users"] = {}
if not data.get("peers"): data["peers"] = {}

class H(BaseHTTPRequestHandler):
    def _json(self, d, c=200):
        self.send_response(c)
        self.send_header("Content-Type","application/json")
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers()
        self.wfile.write(json.dumps(d).encode())
    
    def _html(self, f):
        try:
            p = os.path.join("/app/webapp",f) if os.path.exists("/app") else os.path.join("webapp",f)
            with open(p,"r",encoding="utf-8") as fh: h = fh.read()
            self.send_response(200); self.send_header("Content-Type","text/html"); self.end_headers()
            self.wfile.write(h.encode())
        except: self._json({"error":"Page not found"}, 404)
    
    def do_HEAD(self): self.send_response(200); self.end_headers()
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.end_headers()
    
    def do_GET(self):
        pages = {
            "/":"index.html","/login":"login.html","/register":"register.html",
            "/reset":"reset.html","/dashboard":"dashboard.html","/download":"download.html",
            "/viewer":"viewer.html","/speedtest":"speedtest.html","/status":"status.html",
            "/docs":"docs.html","/blog":"blog.html","/support":"support.html",
            "/forum":"forum.html","/remote":"remote.html","/files":"files.html",
            "/wake":"wake_stream.html","/gamepad":"gamepad.html","/p2p":"p2p.html"
        }
        if self.path in pages: return self._html(pages[self.path])
        if self.path == "/api/status": return self._json({"status":"running","peers":len(data["peers"]),"users":len(data["users"])})
        if self.path == "/peers": return self._json({"peers":list(data["peers"].keys())})
        self._json({"error":"Not found"}, 404)
    
    def do_POST(self):
        l = int(self.headers.get("Content-Length",0))
        b = self.rfile.read(l).decode() if l>0 else "{}"
        try: d = json.loads(b)
        except: d = {}
        
        # ===== AUTH =====
        if self.path == "/api/auth/register":
            email, pw = d.get("email",""), d.get("password","")
            if not email or not pw: return self._json({"error":"Email and password required"}, 400)
            if email in data["users"]: return self._json({"error":"Email already exists"}, 400)
            token = secrets.token_hex(32)
            peer_id = "nexus-" + hashlib.md5(email.encode()).hexdigest()[:12]
            data["users"][email] = {
                "password": hashlib.sha256(pw.encode()).hexdigest(),
                "token": token, "peer_id": peer_id,
                "created": datetime.now().isoformat()
            }
            save(data)
            return self._json({"status":"registered","token":token,"peer_id":peer_id})
        
        if self.path == "/api/auth/login":
            email, pw = d.get("email",""), d.get("password","")
            u = data["users"].get(email)
            if u and u["password"] == hashlib.sha256(pw.encode()).hexdigest():
                return self._json({"status":"ok","token":u["token"],"peer_id":u["peer_id"]})
            return self._json({"error":"Invalid credentials"}, 401)
        
        if self.path == "/api/auth/reset":
            email, new_pw = d.get("email",""), d.get("new_password","")
            if email in data["users"]:
                data["users"][email]["password"] = hashlib.sha256(new_pw.encode()).hexdigest()
                save(data)
                return self._json({"status":"password_reset"})
            return self._json({"error":"Email not found"}, 400)
        
        # ===== DEVICE =====
        if self.path == "/register":
            pid = d.get("peer_id","")
            if pid:
                data["peers"][pid] = {"platform":d.get("platform","?"),"mac":d.get("mac",""),"time":datetime.now().isoformat()}
                save(data)
                return self._json({"status":"registered","peer_id":pid})
            return self._json({"error":"peer_id required"}, 400)
        
        # ===== STREAM =====
        if self.path == "/start_stream":
            sid = f"stream_{int(time.time())}"
            data["streams"][sid] = {"source":d.get("source",""),"target":d.get("target","")}
            save(data)
            return self._json({"status":"streaming","stream_id":sid})
        if self.path == "/send_frame": return self._json({"status":"sent"})
        if self.path == "/get_frame": return self._json({"type":"video","data":"FRAME"})
        if self.path == "/stop_stream": return self._json({"status":"stopped"})
        if self.path == "/wol": return self._json({"status":"wol_sent","success":True})
        
        self._json({"error":"Not found"}, 404)
    
    def log_message(self,*a): pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    print(f"Nexus Remote v4.0 on port {port}")
    HTTPServer(("0.0.0.0",port),H).serve_forever()
