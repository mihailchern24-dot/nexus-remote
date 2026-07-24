#!/usr/bin/env python3
# audio_stream.py - Stream audio from PC to phone
import pyaudio
import wave
import requests
import threading
import time
import base64

class AudioStreamer:
    def __init__(self, server="https://nexus-remote.onrender.com"):
        self.server = server
        self.streaming = False
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 22050
    
    def start_stream(self, target_peer):
        self.streaming = True
        self.target = target_peer
        
        audio = pyaudio.PyAudio()
        stream = audio.open(format=self.format, channels=self.channels,
                           rate=self.rate, input=True, frames_per_buffer=self.chunk)
        
        print(f"[Audio] Streaming to {target_peer}...")
        
        while self.streaming:
            try:
                data = stream.read(self.chunk, exception_on_overflow=False)
                b64 = base64.b64encode(data).decode()
                requests.post(f"{self.server}/send_frame", json={
                    "stream_id": "audio",
                    "from": "audio-source",
                    "target": target_peer,
                    "frame": b64,
                    "type": "audio"
                }, timeout=2)
            except: pass
        
        stream.stop_stream(); stream.close(); audio.terminate()
    
    def stop(self):
        self.streaming = False
        print("[Audio] Stopped")

if __name__ == "__main__":
    print("Nexus Audio Streamer")
    print("Install: pip install pyaudio")
    AudioStreamer().start_stream("my-phone")
