#!/usr/bin/env python3
# multi_monitor.py - Multi-Monitor Support for Nexus Remote
import pyautogui
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageGrab
import io
import time
import threading

class MultiMonitorManager:
    """правление несколькими мониторами"""
    
    def __init__(self):
        self.monitors = self.detect_monitors()
        self.active_monitor = 0
        self.capturing = False
    
    def detect_monitors(self):
        """пределение всех подключенных мониторов"""
        try:
            import screeninfo
            monitors = []
            for i, m in enumerate(screeninfo.get_monitors()):
                monitors.append({
                    'id': i,
                    'name': m.name if m.name else f"Monitor {i+1}",
                    'width': m.width,
                    'height': m.height,
                    'x': m.x,
                    'y': m.y,
                    'is_primary': m.is_primary
                })
            return monitors if monitors else self.fallback_detect()
        except ImportError:
            return self.fallback_detect()
    
    def fallback_detect(self):
        """апасной метод определения мониторов через tkinter"""
        root = tk.Tk()
        root.withdraw()
        
        # олучаем общий размер всех экранов
        total_w = root.winfo_screenwidth()
        total_h = root.winfo_screenheight()
        
        # сли ширина больше 2500, вероятно несколько мониторов
        if total_w > 2500:
            # редполагаем 2 монитора по горизонтали
            return [
                {'id': 0, 'name': 'Monitor 1 (Left)', 'width': total_w//2, 'height': total_h, 'x': 0, 'y': 0, 'is_primary': False},
                {'id': 1, 'name': 'Monitor 2 (Right)', 'width': total_w//2, 'height': total_h, 'x': total_w//2, 'y': 0, 'is_primary': True}
            ]
        elif total_h > 1500:
            # ертикальная конфигурация
            return [
                {'id': 0, 'name': 'Monitor 1 (Top)', 'width': total_w, 'height': total_h//2, 'x': 0, 'y': 0, 'is_primary': True},
                {'id': 1, 'name': 'Monitor 2 (Bottom)', 'width': total_w, 'height': total_h//2, 'x': 0, 'y': total_h//2, 'is_primary': False}
            ]
        
        # дин монитор
        return [{'id': 0, 'name': 'Primary Monitor', 'width': total_w, 'height': total_h, 'x': 0, 'y': 0, 'is_primary': True}]
    
    def capture_monitor(self, monitor_id=None):
        """ахват конкретного монитора"""
        if monitor_id is None:
            monitor_id = self.active_monitor
        
        if monitor_id >= len(self.monitors):
            return None
        
        monitor = self.monitors[monitor_id]
        
        # ахват области монитора
        bbox = (monitor['x'], monitor['y'], 
                monitor['x'] + monitor['width'], 
                monitor['y'] + monitor['height'])
        
        screenshot = ImageGrab.grab(bbox=bbox)
        
        return {
            'image': screenshot,
            'monitor_id': monitor_id,
            'monitor_name': monitor['name'],
            'width': monitor['width'],
            'height': monitor['height']
        }
    
    def capture_all(self):
        """ахват всех мониторов"""
        frames = []
        for i in range(len(self.monitors)):
            frame = self.capture_monitor(i)
            if frame:
                frames.append(frame)
        return frames
    
    def switch_monitor(self, monitor_id):
        """ереключение активного монитора"""
        if 0 <= monitor_id < len(self.monitors):
            self.active_monitor = monitor_id
            return True
        return False
    
    def get_monitor_list(self):
        """Список мониторов для UI"""
        return [f"{m['name']} ({m['width']}x{m['height']})" for m in self.monitors]
    
    def get_monitor_count(self):
        return len(self.monitors)

# ==================== UI Я ЬТ-Т ====================
class MultiMonitorUI:
    def __init__(self, client=None):
        self.manager = MultiMonitorManager()
        self.client = client
        self.monitor_windows = {}  # кна для каждого монитора
        
    def create_monitor_selector(self, parent):
        """Создает панель выбора монитора"""
        frame = tk.Frame(parent, bg='#151530', bd=0, highlightthickness=1, highlightbackground='#2a2a4a')
        
        tk.Label(frame, text="🖥 Monitors", font=('Segoe UI', 12, 'bold'),
                fg='#6366f1', bg='#151530').pack(anchor='w', padx=12, pady=(10, 5))
        
        # нформация о мониторах
        info_frame = tk.Frame(frame, bg='#151530')
        info_frame.pack(fill=tk.X, padx=12, pady=(0, 8))
        
        monitor_list = self.manager.get_monitor_list()
        monitor_count = self.manager.get_monitor_count()
        
        tk.Label(info_frame, text=f"Detected: {monitor_count} monitor(s)",
                font=('Segoe UI', 9), fg='#888', bg='#151530').pack(anchor='w')
        
        # нопки для каждого монитора
        self.monitor_buttons = []
        for i, name in enumerate(monitor_list):
            is_active = i == self.manager.active_monitor
            bg_color = '#6366f1' if is_active else '#0f0f1a'
            fg_color = '#fff' if is_active else '#888'
            
            btn = tk.Button(info_frame, text=f"🖥 {name}",
                          font=('Segoe UI', 9, 'bold'),
                          bg=bg_color, fg=fg_color,
                          activebackground='#6366f1',
                          relief=tk.FLAT, bd=0,
                          cursor='hand2',
                          command=lambda idx=i: self.switch_monitor(idx))
            btn.pack(fill=tk.X, pady=2)
            self.monitor_buttons.append(btn)
        
        # нопка "Capture All"
        self.capture_all_btn = tk.Button(info_frame, text="📸 Capture All Monitors",
                                        font=('Segoe UI', 9),
                                        bg='#22c55e', fg='#fff',
                                        relief=tk.FLAT, bd=0,
                                        cursor='hand2',
                                        command=self.capture_all_monitors)
        self.capture_all_btn.pack(fill=tk.X, pady=(8, 0))
        
        return frame
    
    def switch_monitor(self, monitor_id):
        """ереключение монитора"""
        if self.manager.switch_monitor(monitor_id):
            # бновляем кнопки
            for i, btn in enumerate(self.monitor_buttons):
                if i == monitor_id:
                    btn.config(bg='#6366f1', fg='#fff')
                else:
                    btn.config(bg='#0f0f1a', fg='#888')
    
    def capture_all_monitors(self):
        """ахват всех мониторов и отправка"""
        if not self.client:
            return
        
        frames = self.manager.capture_all()
        
        for i, frame in enumerate(frames):
            # ткрываем окно для каждого монитора
            if i not in self.monitor_windows:
                self.create_monitor_window(i, frame)
            
            # тправляем кадр
            buf = io.BytesIO()
            frame['image'].save(buf, format='JPEG', quality=50)
            self.client.send_frame(buf.getvalue())
            
            time.sleep(0.1)
    
    def create_monitor_window(self, monitor_id, frame):
        """Создает отдельное окно для монитора"""
        window = tk.Toplevel()
        window.title(f"Nexus Remote - {frame['monitor_name']}")
        window.geometry(f"{frame['width']//2}x{frame['height']//2}")
        window.configure(bg='#000')
        
        canvas = tk.Canvas(window, bg='#000', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        self.monitor_windows[monitor_id] = {
            'window': window,
            'canvas': canvas
        }

# нтеграция с основным клиентом
def add_multi_monitor_to_client(client_ui):
    """обавляет поддержку мульти-монитора в существующий UI"""
    monitor_manager = MultiMonitorManager()
    monitor_ui = MultiMonitorUI(client_ui.client)
    
    # обавляем вкладку Monitors
    monitors_tab = tk.Frame(client_ui.notebook, bg=client_ui.bg)
    client_ui.notebook.add(monitors_tab, text="  🖥 Monitors  ")
    
    selector = monitor_ui.create_monitor_selector(monitors_tab)
    selector.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Сохраняем ссылки
    client_ui.monitor_manager = monitor_manager
    client_ui.monitor_ui = monitor_ui
    
    return monitor_manager

if __name__ == "__main__":
    # Тест мульти-монитора
    manager = MultiMonitorManager()
    monitors = manager.detect_monitors()
    
    print(f"Detected {len(monitors)} monitor(s):")
    for m in monitors:
        primary = " (Primary)" if m['is_primary'] else ""
        print(f"  {m['name']}: {m['width']}x{m['height']}{primary}")
    
    # Тест захвата
    frame = manager.capture_monitor(0)
    if frame:
        print(f"\nCaptured: {frame['width']}x{frame['height']}")
        frame['image'].save("test_monitor_capture.jpg")
        print("Saved: test_monitor_capture.jpg")
