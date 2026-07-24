#!/usr/bin/env python3
import json, os, time, hashlib, secrets, sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

DB = "/app/nexus_auth.db" if os.path.exists("/app") else "nexus_auth.db"

class DB:
    def __init__(self):
        self.c = sqlite3.connect(DB, check_same_thread=False)
        self.c.executescript("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE,pass TEXT,token TEXT,peer TEXT,created TEXT)")
        self.c.commit()
    def reg(self,e,p):
        try:
            t=secrets.token_hex(32); ph=hashlib.sha256(p.encode()).hexdigest(); pr=f"nexus-{hashlib.md5(e.encode()).hexdigest()[:12]}"
            self.c.execute("INSERT INTO users(email,pass,token,peer,created) VALUES(?,?,?,?,?)",(e,ph,t,pr,datetime.now().isoformat()))
            self.c.commit(); return {"status":"registered","token":t,"peer_id":pr}
        except: return {"error":"Email exists"}
    def login(self,e,p):
        ph=hashlib.sha256(p.encode()).hexdigest()
        r=self.c.execute("SELECT token,peer FROM users WHERE email=? AND pass=?",(e,ph)).fetchone()
        if r: return {"status":"ok","token":r[0],"peer_id":r[1]}
        return {"error":"Invalid credentials"}
    def reset(self,e,p):
        ph=hashlib.sha256(p.encode()).hexdigest()
        self.c.execute("UPDATE users SET pass=? WHERE email=?",(ph,e)); self.c.commit()
        return self.c.rowcount>0

db=DB()
peers={}
streams={}
messages={}

class H(BaseHTTPRequestHandler):
    def _json(self,d,c=200):
        self.send_response(c); self.send_header("Content-Type","application/json"); self.send_header("Access-Control-Allow-Origin","*"); self.end_headers()
        self.wfile.write(json.dumps(d).encode())
    def _html(self,f):
        try:
            p=os.path.join("/app/webapp",f) if os.path.exists("/app") else os.path.join("webapp",f)
            with open(p,"r",encoding="utf-8") as fh: h=fh.read()
            self.send_response(200); self.send_header("Content-Type","text/html"); self.end_headers(); self.wfile.write(h.encode())
        except: self._json({"error":"Page not found"},404)
    def do_HEAD(self): self.send_response(200); self.end_headers()
    def do_OPTIONS(self):
        self.send_response(200); self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS"); self.send_header("Access-Control-Allow-Headers","Content-Type"); self.end_headers()
    def do_GET(self):
        pages={"/":"index.html","/login":"login.html","/register":"register.html","/reset":"reset.html","/dashboard":"dashboard.html","/download":"download.html","/viewer":"viewer.html","/speedtest":"speedtest.html","/status":"status.html","/docs":"docs.html","/blog":"blog.html","/support":"support.html","/forum":"forum.html","/remote":"remote.html","/files":"files.html","/wake":"wake_stream.html","/gamepad":"gamepad.html","/p2p":"p2p.html"}
        if self.path in pages: return self._html(pages[self.path])
        if self.path=="/api/status": return self._json({"status":"running","server":"Nexus Remote v4.0","peers":len(peers),"streams":len(streams)})
        if self.path=="/peers": return self._json({"peers":list(peers.keys()),"count":len(peers)})
        self._json({"error":"Not found"},404)
    def do_POST(self):
        l=int(self.headers.get("Content-Length",0)); b=self.rfile.read(l).decode() if l>0 else "{}"
        try: d=json.loads(b)
        except: d={}
        if self.path=="/api/auth/register": return self._json(db.reg(d.get("email",""),d.get("password","")))
        if self.path=="/api/auth/login": return self._json(db.login(d.get("email",""),d.get("password","")))
        if self.path=="/api/auth/reset":
            if db.reset(d.get("email",""),d.get("new_password","")): return self._json({"status":"password_reset"})
            return self._json({"error":"Not found"},400)
        if self.path=="/register":
            p=d.get("peer_id","")
            if p: peers[p]={"platform":d.get("platform","?"),"time":datetime.now().isoformat()}; return self._json({"status":"registered","peer_id":p})
            return self._json({"error":"peer_id required"},400)
        if self.path=="/start_stream":
            s=f"stream_{int(time.time())}"; streams[s]={"source":d.get("source",""),"target":d.get("target",""),"status":"active"}
            return self._json({"status":"streaming","stream_id":s})
        if self.path=="/send_frame": return self._json({"status":"sent"})
        if self.path=="/get_frame": return self._json({"type":"video","data":"TEST_FRAME","from":"test"})
        if self.path=="/stop_stream":
            sid=d.get("stream_id","")
            if sid in streams: streams[sid]["status"]="stopped"; return self._json({"status":"stopped"})
            return self._json({"error":"Not found"},404)
        if self.path=="/wol": return self._json({"status":"wol_sent","success":True})
        if self.path=="/clipboard": return self._json({"status":"synced"})
        self._json({"error":"Not found"},404)
    def log_message(self,*a): pass

if __name__=="__main__":
    p=int(os.environ.get("PORT",10000))
    print(f"Nexus Remote v4.0 on port {p}")
    HTTPServer(("0.0.0.0",p),H).serve_forever()
