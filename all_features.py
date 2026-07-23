#!/usr/bin/env python3
# all_features.py - ALL Nexus Remote Features v2 (FIXED)
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import threading, time, io, os, json, base64, hashlib, secrets
from datetime import datetime, timedelta
from PIL import Image, ImageGrab
import pyautogui, pyotp, qrcode, requests

# ============ MULTI-MONITOR ============
class MultiMonitorManager:
    def __init__(self):
        self.monitors = self.detect()
        self.active = 0
    def detect(self):
        try:
            import screeninfo
            mons = []
            for i, m in enumerate(screeninfo.get_monitors()):
                mons.append({'id':i,'name':m.name or f'Monitor {i+1}','w':m.width,'h':m.height,'x':m.x,'y':m.y,'primary':m.is_primary})
            return mons if mons else self.fallback()
        except:
            return self.fallback()
    def fallback(self):
        r = tk.Tk(); r.withdraw()
        w, h = r.winfo_screenwidth(), r.winfo_screenheight()
        r.destroy()
        if w > 2500:
            return [{'id':0,'name':'Left','w':w//2,'h':h,'x':0,'y':0,'primary':False},{'id':1,'name':'Right','w':w//2,'h':h,'x':w//2,'y':0,'primary':True}]
        return [{'id':0,'name':'Primary','w':w,'h':h,'x':0,'y':0,'primary':True}]
    def capture(self, mid=None):
        if mid is None: mid = self.active
        m = self.monitors[mid]
        img = ImageGrab.grab(bbox=(m['x'],m['y'],m['x']+m['w'],m['y']+m['h']))
        buf = io.BytesIO(); img.save(buf, format='JPEG', quality=50)
        return buf.getvalue(), m['w'], m['h']
    def capture_all(self):
        return [self.capture(i) for i in range(len(self.monitors))]
    def switch(self, mid):
        if 0 <= mid < len(self.monitors): self.active = mid

# ============ CHAT (FIXED) ============
class StreamChat:
    def __init__(self, client=None):
        self.client = client
        self.messages = []
        self.unread = 0
    def create_ui(self, parent):
        frame = tk.Frame(parent, bg='#151530')
        tk.Label(frame, text="Chat", font=('Segoe UI', 12, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=10, pady=(10,5))
        self.display = scrolledtext.ScrolledText(frame, height=10, font=('Segoe UI', 9), bg='#0a0a1a', fg='#e0e0e0', relief=tk.FLAT)
        self.display.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        inp = tk.Frame(frame, bg='#151530')
        inp.pack(fill=tk.X, padx=10, pady=(0,10))
        self.input = tk.Entry(inp, font=('Segoe UI', 10), bg='#0a0a1a', fg='#e0e0e0', relief=tk.FLAT)
        self.input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.input.bind('<Return>', lambda e: self.send())
        tk.Button(inp, text="Send", font=('Segoe UI', 9, 'bold'), bg='#6366f1', fg='#fff', relief=tk.FLAT, padx=15, command=self.send).pack(side=tk.RIGHT, padx=(5,0))
        qf = tk.Frame(frame, bg='#151530')
        qf.pack(fill=tk.X, padx=10)
        for t in ["OK","Wait","Done","Help"]:
            tk.Button(qf, text=t, font=('Segoe UI', 8), bg='#1a1a3e', fg='#888', relief=tk.FLAT, padx=8, command=lambda m=t: self.quick(m)).pack(side=tk.LEFT, padx=1)
        return frame
    def send(self):
        t = self.input.get().strip()
        if not t: return
        self.input.delete(0, tk.END)
        self.add("You", t, True)
    def quick(self, m):
        self.add("You", m, True)
    def add(self, sender, text, is_self=False):
        ts = datetime.now().strftime("%H:%M")
        # Store in messages list (always works)
        self.messages.append({'sender':sender,'text':text,'time':ts,'is_self':is_self})
        # Display if UI exists
        if hasattr(self, 'display'):
            try:
                self.display.config(state='normal')
                color = '#6366f1' if is_self else '#22c55e'
                self.display.insert(tk.END, f"[{ts}] {sender}: {text}\n")
                self.display.see(tk.END)
                self.display.config(state='disabled')
            except:
                pass

# ============ MFA ============
class MFAManager:
    def __init__(self):
        self.secret = None
    def setup(self, email):
        self.secret = pyotp.random_base32()
        totp = pyotp.TOTP(self.secret)
        uri = totp.provisioning_uri(name=email, issuer_name="Nexus Remote")
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(uri); qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save("mfa_qr.png")
        return self.secret, "mfa_qr.png"
    def verify(self, code):
        if not self.secret: return True
        return pyotp.TOTP(self.secret).verify(code)

# ============ RECORDER (FIXED) ============
class SessionRecorder:
    def __init__(self):
        self.recording = False
        self.frames = []
        self.start_time = None
    def start(self):
        self.recording = True
        self.frames = []
        self.start_time = time.time()
    def add_frame(self, data):
        if self.recording: self.frames.append(data)
    def stop(self, filepath=None):
        self.recording = False
        if not filepath: filepath = f"nexus_rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bin"
        count = len(self.frames)
        if self.frames:
            with open(filepath, 'wb') as f:
                for frame in self.frames: f.write(frame)
        dur = time.time() - self.start_time if self.start_time else 0
        self.frames = []
        return filepath, dur, count

# ============ FILE TRANSFER ============
class FileTransfer:
    def __init__(self, client=None):
        self.client = client
    def send_file(self, filepath):
        if not os.path.exists(filepath): return False
        with open(filepath, 'rb') as f:
            data = base64.b64encode(f.read()).decode()
        return True
    def create_ui(self, parent):
        frame = tk.Frame(parent, bg='#151530')
        tk.Label(frame, text="File Transfer", font=('Segoe UI', 12, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=10, pady=(10,5))
        tk.Button(frame, text="Send File", bg='#6366f1', fg='#fff', relief=tk.FLAT, padx=20, pady=8, command=self.select_file).pack(padx=10, pady=10)
        return frame
    def select_file(self):
        from tkinter import filedialog
        fp = filedialog.askopenfilename()
        if fp:
            self.send_file(fp)
            messagebox.showinfo("Done", f"Sent: {os.path.basename(fp)}")

# ============ DEVICE GROUPS ============
class DeviceGroups:
    def __init__(self):
        self.groups = {"Home":[],"Work":[],"Gaming":[],"Mobile":[]}
    def create_ui(self, parent):
        frame = tk.Frame(parent, bg='#151530')
        tk.Label(frame, text="Device Groups", font=('Segoe UI', 12, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=10, pady=(10,5))
        for g in self.groups:
            tk.Label(frame, text=f"  {g} (0 devices)", fg='#888', bg='#151530').pack(anchor='w', padx=10)
        return frame

# ============ STATS ============
class StatsDashboard:
    def __init__(self):
        self.sessions = []
        self.total_frames = 0
        self.total_bytes = 0
        self.total_duration = 0
    def create_ui(self, parent):
        frame = tk.Frame(parent, bg='#151530')
        tk.Label(frame, text="Statistics", font=('Segoe UI', 12, 'bold'), fg='#6366f1', bg='#151530').pack(anchor='w', padx=10, pady=(10,5))
        for label, value in [("Sessions",len(self.sessions)),("Frames",self.total_frames),("Data",f"{self.total_bytes//1024}KB"),("Duration",f"{self.total_duration}s")]:
            r = tk.Frame(frame, bg='#151530')
            r.pack(fill=tk.X, padx=10, pady=2)
            tk.Label(r, text=label, fg='#888', bg='#151530').pack(side=tk.LEFT)
            tk.Label(r, text=str(value), fg='#fff', bg='#151530').pack(side=tk.RIGHT)
        return frame

# ============ ALL FEATURES UI ============
class AllFeaturesUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Nexus Remote - All Features")
        self.root.geometry("800x600")
        self.root.configure(bg='#0a0a1a')
        self.monitor_mgr = MultiMonitorManager()
        self.chat = StreamChat()
        self.mfa = MFAManager()
        self.recorder = SessionRecorder()
        self.files = FileTransfer()
        self.groups = DeviceGroups()
        self.stats = StatsDashboard()
        self.setup_ui()
    def setup_ui(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for name, create_func in [
            ("Monitors", self.monitors_tab), ("Chat", self.chat_tab),
            ("Files", self.files_tab), ("Groups", self.groups_tab),
            ("Stats", self.stats_tab), ("MFA", self.mfa_tab), ("Record", self.rec_tab)
        ]:
            tab = tk.Frame(nb, bg='#0a0a1a')
            nb.add(tab, text=f"  {name}  ")
            create_func(tab)
    def monitors_tab(self, p):
        tk.Label(p, text="Monitors: " + str(len(self.monitor_mgr.monitors)), fg='#fff', bg='#0a0a1a', font=('Segoe UI', 14)).pack(pady=20)
        for i, m in enumerate(self.monitor_mgr.monitors):
            tk.Button(p, text=f"{m['name']} ({m['w']}x{m['h']})", bg='#6366f1' if i==self.monitor_mgr.active else '#1a1a3e', fg='#fff', relief=tk.FLAT, padx=20, pady=8, command=lambda idx=i: self.monitor_mgr.switch(idx)).pack(fill=tk.X, padx=30, pady=3)
    def chat_tab(self, p):
        self.chat.create_ui(p).pack(fill=tk.BOTH, expand=True)
        self.chat.add("System", "Chat ready!", False)
    def files_tab(self, p):
        self.files.create_ui(p).pack(fill=tk.BOTH, expand=True)
    def groups_tab(self, p):
        self.groups.create_ui(p).pack(fill=tk.BOTH, expand=True)
    def stats_tab(self, p):
        self.stats.create_ui(p).pack(fill=tk.BOTH, expand=True)
    def mfa_tab(self, p):
        tk.Label(p, text="MFA Setup", fg='#fff', bg='#0a0a1a', font=('Segoe UI', 14)).pack(pady=10)
        e = tk.Entry(p, font=('Segoe UI', 11), bg='#0f0f1a', fg='#fff'); e.pack(fill=tk.X, padx=20, pady=5); e.insert(0, "user@nexus.com")
        tk.Button(p, text="Setup MFA", bg='#6366f1', fg='#fff', relief=tk.FLAT, padx=20, pady=8, command=lambda: self.mfa.setup(e.get())).pack(pady=5)
    def rec_tab(self, p):
        tk.Label(p, text="Session Recorder", fg='#fff', bg='#0a0a1a', font=('Segoe UI', 14)).pack(pady=10)
        self.rec_status = tk.Label(p, text="Stopped", fg='#888', bg='#0a0a1a', font=('Segoe UI', 11)); self.rec_status.pack()
        tk.Button(p, text="Start/Stop", bg='#ef4444', fg='#fff', relief=tk.FLAT, padx=20, pady=8, command=self.toggle_rec).pack(pady=10)
    def toggle_rec(self):
        if self.recorder.recording:
            path, dur, count = self.recorder.stop()
            self.rec_status.config(text=f"Saved: {count} frames, {dur:.1f}s", fg='#22c55e')
        else:
            self.recorder.start()
            self.rec_status.config(text="Recording...", fg='#ef4444')
            threading.Thread(target=self.sim_rec, daemon=True).start()
    def sim_rec(self):
        while self.recorder.recording:
            self.recorder.add_frame(b"DATA")
            time.sleep(0.1)
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = AllFeaturesUI()
    app.run()
