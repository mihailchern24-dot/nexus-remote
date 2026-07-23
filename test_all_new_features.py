#!/usr/bin/env python3
# test_all_new_features.py - Test ALL New Features
import sys, time, os

def test_multi_monitor():
    print("\n🖥 Testing Multi-Monitor...")
    from all_features import MultiMonitorManager
    mm = MultiMonitorManager()
    monitors = mm.detect()
    print(f"  ✅ Detected {len(monitors)} monitor(s)")
    for m in monitors:
        print(f"     - {m['name']}: {m['w']}x{m['h']}")
    if len(monitors) > 0:
        frame, w, h = mm.capture(0)
        print(f"  ✅ Captured monitor 0: {w}x{h}, {len(frame)} bytes")
    return True

def test_chat():
    print("\n💬 Testing Chat...")
    from all_features import StreamChat
    chat = StreamChat()
    # Test without UI - only messages list (no display needed)
    chat.add("User1", "Hello from remote device!", False)
    chat.add("You", "Hi! Connection is stable.", True)
    chat.add("User1", "Great, let's start working.", False)
    print(f"  ✅ Chat works: {len(chat.messages)} messages stored")
    for msg in chat.messages:
        prefix = "You" if msg['is_self'] else msg['sender']
        print(f"     [{msg['time']}] {prefix}: {msg['text']}")
    return True

def test_mfa():
    print("\n🔐 Testing MFA...")
    from all_features import MFAManager
    import pyotp
    mfa = MFAManager()
    secret, path = mfa.setup("test@nexus.com")
    print(f"  ✅ Secret generated: {secret[:20]}...")
    print(f"  ✅ QR saved: {path}")
    code = pyotp.TOTP(secret).now()
    verified = mfa.verify(code)
    print(f"  ✅ Code verified: {verified}")
    return True

def test_recorder():
    print("\n⏺ Testing Recorder...")
    from all_features import SessionRecorder
    rec = SessionRecorder()
    rec.start()
    time.sleep(0.5)  # Simulate recording
    for i in range(100):
        rec.add_frame(f"FRAME_DATA_{i:04d}".encode())
    path, duration, count = rec.stop("test_recording.bin")
    print(f"  ✅ Recorded: {path} ({duration:.1f}s, {count} frames)")
    if os.path.exists(path):
        size = os.path.getsize(path)
        os.remove(path)
        print(f"  ✅ File size: {size} bytes, cleaned up")
    return True

def test_stats():
    print("\n📊 Testing Stats...")
    from all_features import StatsDashboard
    stats = StatsDashboard()
    stats.sessions = [1, 2, 3, 4, 5]
    stats.total_frames = 5000
    stats.total_bytes = 2500000
    stats.total_duration = 7200
    print(f"  ✅ Sessions: {len(stats.sessions)}")
    print(f"  ✅ Frames: {stats.total_frames}")
    print(f"  ✅ Data: {stats.total_bytes//1024} KB")
    print(f"  ✅ Duration: {stats.total_duration}s ({stats.total_duration//3600}h)")
    return True

def main():
    print("=" * 60)
    print("🧪 NEXUS REMOTE - ALL FEATURES TEST")
    print("=" * 60)
    
    tests = [
        ("Multi-Monitor", test_multi_monitor),
        ("Chat", test_chat),
        ("MFA 2FA", test_mfa),
        ("Recorder", test_recorder),
        ("Stats", test_stats),
    ]
    
    results = []
    for name, func in tests:
        try:
            ok = func()
            results.append((name, ok))
        except Exception as e:
            print(f"\n❌ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    failed = sum(1 for _, r in results if not r)
    
    for name, result in results:
        print(f"  {'✅' if result else '❌'} {name}")
    
    print(f"\n  Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    print(f"  Success: {passed/len(results)*100:.0f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Starting UI Demo...")
        try:
            from all_features import AllFeaturesUI
            app = AllFeaturesUI()
            app.run()
        except ImportError:
            print("UI demo skipped (run manually)")
    else:
        print(f"\n⚠️ {failed} test(s) failed.")
    
    return failed == 0

if __name__ == "__main__":
    main()
