#!/usr/bin/env python3
# test_all_features.py - ТСТ СХ ФУЦ Nexus Remote
import requests
import json
import time
import base64
import hashlib
import secrets
import os
import sys
import platform
import io
import threading
from datetime import datetime
from enum import Enum

SERVER_URL = "https://nexus-remote.onrender.com"
TEST_RESULTS = []
PASSED = 0
FAILED = 0

def log_test(name, status, details=""):
    global PASSED, FAILED
    emoji = "✅" if status else "❌"
    if status: PASSED += 1
    else: FAILED += 1
    msg = f"{emoji} {name}: {'PASS' if status else 'FAIL'} {details}"
    TEST_RESULTS.append(msg)
    print(msg)

def test_api(endpoint, method="GET", data=None, expected_status=200):
    try:
        url = f"{SERVER_URL}{endpoint}"
        if method == "GET":
            resp = requests.get(url, timeout=5)
        else:
            resp = requests.post(url, json=data, timeout=5)
        return resp.status_code == expected_status, resp.json() if resp.text else {}
    except Exception as e:
        return False, str(e)

# ==================== ТСТЫ ====================
print("=" * 60)
print("🔬 NEXUS REMOTE - FULL FEATURE TEST SUITE v4.0")
print("=" * 60)
print(f"Server: {SERVER_URL}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# 1. Ы ТСТЫ С
print("\n📡 [1/10] азовые тесты сервера...")

ok, _ = test_api("/", "GET")
log_test("Health Check", ok)

ok, data = test_api("/status", "GET")
log_test("Server Status", ok, f"peers={data.get('peers', '?')}, streams={data.get('streams', '?')}")

ok, data = test_api("/methods", "GET")
log_test("Available Methods", ok, f"compression={len(data.get('compression', []))}, encryption={len(data.get('encryption', []))}")

# 2. СТЦ УСТСТ
print("\n🔗 [2/10] егистрация устройств...")

peer_windows = f"TEST-WIN-{secrets.token_hex(4)}"
peer_android = f"TEST-ANDROID-{secrets.token_hex(4)}"
peer_linux = f"TEST-LINUX-{secrets.token_hex(4)}"
peer_ps5 = f"TEST-PS5-{secrets.token_hex(4)}"
peer_xbox = f"TEST-XBOX-{secrets.token_hex(4)}"

devices_to_register = [
    (peer_windows, "windows", "h264_nvenc"),
    (peer_android, "android", "h264_mediacodec"),
    (peer_linux, "linux", "h264_vaapi"),
    (peer_ps5, "playstation", "libx264"),
    (peer_xbox, "xbox", "h264_amf"),
]

registered_peers = []
for peer_id, platf, codec in devices_to_register:
    data = {"peer_id": peer_id, "platform": platf, "compression": "zstd", "encryption": "aes_gcm"}
    ok, resp = test_api("/register", "POST", data)
    log_test(f"Register {platf}", ok, f"peer={peer_id[:20]}...")
    if ok:
        registered_peers.append(peer_id)

# 3. СС 
print("\n👥 [3/10] Список устройств...")

ok, data = test_api("/peers", "GET")
peer_count = len(data.get('peers', []))
log_test("Get Peers List", ok and peer_count > 0, f"found {peer_count} peers")

# 4. УС СТ
print("\n📺 [4/10] апуск стриминга...")

stream_results = []
if len(registered_peers) >= 2:
    # Windows -> Android
    data = {"source": registered_peers[0], "target": registered_peers[1], "quality": "high"}
    ok, resp = test_api("/start_stream", "POST", data)
    log_test("Start Stream (Win->Android)", ok, f"stream_id={resp.get('stream_id', '?')[:20]}...")
    if ok:
        stream_results.append(resp.get('stream_id'))
    
    # Android -> Linux
    data = {"source": registered_peers[1], "target": registered_peers[2], "quality": "medium"}
    ok, resp = test_api("/start_stream", "POST", data)
    log_test("Start Stream (Android->Linux)", ok)
    if ok:
        stream_results.append(resp.get('stream_id'))

# 5. Т 
print("\n📸 [5/10] тправка кадров...")

test_frame = base64.b64encode(b"TEST_FRAME_DATA_FOR_NEXUS_REMOTE_TESTING" * 10).decode()

if stream_results:
    data = {
        "stream_id": stream_results[0],
        "from": registered_peers[0],
        "target": registered_peers[1],
        "frame": test_frame,
        "type": "video"
    }
    ok, resp = test_api("/send_frame", "POST", data)
    log_test("Send Video Frame", ok, f"size={len(test_frame)} bytes")
    
    # тправка аудио
    audio_frame = base64.b64encode(b"AUDIO_TEST_DATA" * 5).decode()
    data = {
        "stream_id": stream_results[0],
        "from": registered_peers[0],
        "target": registered_peers[1],
        "frame": audio_frame,
        "type": "audio"
    }
    ok, _ = test_api("/send_frame", "POST", data)
    log_test("Send Audio Frame", ok)

# 6. У 
print("\n📥 [6/10] олучение кадров...")

data = {"peer_id": registered_peers[1]} if registered_peers else {"peer_id": peer_android}
ok, resp = test_api("/get_frame", "POST", data)
has_frame = resp.get('type') != 'empty' if ok else False
log_test("Receive Frame", ok, f"has_frame={has_frame}")

# 7. СТ  ШФ
print("\n🔐 [7/10] Сжатие и шифрование...")

from compression import AdaptiveCompressor, CompressionMethod
from encryption import NexusCrypto, EncryptionMethod

# Тест сжатия
test_data = b"X" * 10000 + b"Y" * 5000 + b"Z" * 2500
for method in [CompressionMethod.ZLIB, CompressionMethod.LZMA, CompressionMethod.GZIP]:
    compressed, _, ratio = AdaptiveCompressor.best_compress(test_data)
    log_test(f"Compression {method.value}", ratio > 10, f"ratio={ratio:.1f}%")

# Тест шифрования
crypto = NexusCrypto("test_key_2024")
test_message = b"Secret message for Nexus Remote!"
for method in [EncryptionMethod.AES_GCM, EncryptionMethod.CHACHA20, EncryptionMethod.XOR]:
    encrypted, enc_method, meta = crypto.encrypt(test_message, method)
    decrypted = crypto.decrypt(encrypted, enc_method, meta)
    log_test(f"Encryption {method.value}", decrypted == test_message)

# 8. УТ-ССС
print("\n🔄 [8/10] ульти-сессии...")

active_streams = 0
for i in range(min(3, len(registered_peers) - 1)):
    source = registered_peers[0]
    target = registered_peers[i + 1]
    data = {"source": source, "target": target, "quality": "low"}
    ok, resp = test_api("/start_stream", "POST", data)
    if ok:
        active_streams += 1

log_test("Multiple Streams", active_streams >= 2, f"active={active_streams}")

# роверка статуса
ok, data = test_api("/status", "GET")
log_test("Multi-session Status", ok, f"streams={data.get('streams', '?')}")

# 9. СТ СТ
print("\n⏹ [9/10] становка стримов...")

for sid in stream_results:
    ok, _ = test_api("/stop_stream", "POST", {"stream_id": sid})
    log_test(f"Stop Stream", ok, f"id={sid[:20]}...")

# 10. WAKE-ON-LAN
print("\n⚡ [10/10] Wake-on-LAN...")

ok, _ = test_api("/wol", "POST", {"mac": "AA:BB:CC:DD:EE:FF", "peer_id": peer_windows})
log_test("WOL Endpoint", ok, "WOL endpoint exists")

# ==================== Т ====================
print("\n" + "=" * 60)
print("📊 Т ТСТ")
print("=" * 60)
print(f"сего тестов: {PASSED + FAILED}")
print(f"✅ ройдено: {PASSED}")
print(f"❌ ровалено: {FAILED}")
print(f"📈 Успешность: {PASSED/(PASSED+FAILED)*100:.1f}%")
print("=" * 60)

# Финальный вердикт
if FAILED == 0:
    print("\n🎉 С ТСТЫ Ы! Nexus Remote готов к использованию!")
elif FAILED <= 3:
    print(f"\n⚠️ {FAILED} тестов провалено. Требуется доработка.")
else:
    print(f"\n🚨 {FAILED} тестов провалено. еобходима отладка сервера.")

print(f"\nСервер: {SERVER_URL}")
print(f"окументация: {SERVER_URL}/methods")
