from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import engine, Base
from app.auth import router as auth_router
from app.devices import router as devices_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(title="Nexus Remote API", description="Remote desktop control API", version="0.4.1", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(auth_router)
app.include_router(devices_router)

class ConnectionManager:
    def __init__(self):
        self.connections = {}
    async def connect_agent(self, peer_id: str, websocket: WebSocket):
        await websocket.accept()
        if peer_id not in self.connections:
            self.connections[peer_id] = {"agent": None, "viewers": set()}
        self.connections[peer_id]["agent"] = websocket
    async def connect_viewer(self, peer_id: str, websocket: WebSocket):
        await websocket.accept()
        if peer_id not in self.connections:
            self.connections[peer_id] = {"agent": None, "viewers": set()}
        self.connections[peer_id]["viewers"].add(websocket)
    def disconnect(self, peer_id: str, websocket: WebSocket):
        if peer_id in self.connections:
            if self.connections[peer_id]["agent"] == websocket:
                self.connections[peer_id]["agent"] = None
            else:
                self.connections[peer_id]["viewers"].discard(websocket)
            if not self.connections[peer_id]["agent"] and not self.connections[peer_id]["viewers"]:
                del self.connections[peer_id]
    async def broadcast_to_viewers(self, peer_id: str, message: bytes):
        if peer_id in self.connections:
            dead = set()
            for viewer in self.connections[peer_id]["viewers"]:
                try:
                    await viewer.send_bytes(message)
                except:
                    dead.add(viewer)
            for viewer in dead:
                self.connections[peer_id]["viewers"].discard(viewer)
    async def send_to_agent(self, peer_id: str, message: str):
        if peer_id in self.connections and self.connections[peer_id]["agent"]:
            try:
                await self.connections[peer_id]["agent"].send_text(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws/agent/{peer_id}")
async def agent_stream(websocket: WebSocket, peer_id: str):
    await manager.connect_agent(peer_id, websocket)
    try:
        while True:
            data = await websocket.receive_bytes()
            await manager.broadcast_to_viewers(peer_id, data)
    except WebSocketDisconnect:
        manager.disconnect(peer_id, websocket)
    except Exception as e:
        manager.disconnect(peer_id, websocket)

@app.websocket("/ws/view/{peer_id}")
async def viewer_stream(websocket: WebSocket, peer_id: str):
    await manager.connect_viewer(peer_id, websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            await manager.send_to_agent(peer_id, msg)
    except WebSocketDisconnect:
        manager.disconnect(peer_id, websocket)
    except Exception as e:
        manager.disconnect(peer_id, websocket)

SPLASH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0b0f19">
<title>Nexus Remote</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0f172a;color:#e2e8f0;font-family:Inter,system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;overflow:hidden}
.logo{width:80px;height:80px;margin-bottom:24px}
.title{font-size:28px;font-weight:800;background:linear-gradient(90deg,#38bdf8,#818cf8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:2px}
.subtitle{margin-top:8px;font-size:12px;color:#475569;letter-spacing:3px;text-transform:uppercase}
.links{margin-top:32px;display:flex;gap:16px}
.links a{color:#38bdf8;text-decoration:none;font-size:14px;opacity:.7;transition:opacity .2s}
.links a:hover{opacity:1}
</style>
</head>
<body>
<svg class="logo" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
<defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#38bdf8"/><stop offset="100%" stop-color="#818cf8"/></linearGradient></defs>
<circle cx="50" cy="50" r="10" fill="url(#g)"/>
<line x1="50" y1="50" x2="22" y2="22" stroke="url(#g)" stroke-width="5" stroke-linecap="round"/>
<line x1="50" y1="50" x2="78" y2="22" stroke="url(#g)" stroke-width="5" stroke-linecap="round"/>
<line x1="50" y1="50" x2="22" y2="78" stroke="url(#g)" stroke-width="5" stroke-linecap="round"/>
<line x1="50" y1="50" x2="78" y2="78" stroke="url(#g)" stroke-width="5" stroke-linecap="round"/>
<circle cx="22" cy="22" r="6" fill="#0f172a" stroke="url(#g)" stroke-width="3"/>
<circle cx="78" cy="22" r="6" fill="#0f172a" stroke="url(#g)" stroke-width="3"/>
<circle cx="22" cy="78" r="6" fill="#0f172a" stroke="url(#g)" stroke-width="3"/>
<circle cx="78" cy="78" r="6" fill="#0f172a" stroke="url(#g)" stroke-width="3"/>
<text x="50" y="54" text-anchor="middle" fill="#0f172a" font-size="10" font-weight="800" font-family="Inter,sans-serif">N</text>
</svg>
<div class="title">NEXUS REMOTE</div>
<div class="subtitle">Remote Control System</div>
<div class="links">
<a href="/docs">API Docs</a>
<a href="/health">Health</a>
<a href="https://nexus-frontend-psi-two.vercel.app" target="_blank">Dashboard</a>
</div>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return SPLASH_HTML

@app.head("/")
async def root_head():
    return HTMLResponse(content="", status_code=200)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "nexus-remote", "version": "0.4.1"}

@app.head("/health")
async def health_head():
    return {"status": "ok"}
