# -*- coding: utf-8 -*-
"""起動ログをフルキャプチャ。最大120秒、連続5秒無反応で終了"""
import serial, time, sys

PORT="COM3"; BAUD=9600; MAX_SEC=120

with serial.Serial(PORT, BAUD, timeout=0.3) as ser:
    print(f"[ready] {PORT}@{BAUD} — いつでも機器の電源投入OK。最大{MAX_SEC}秒")
    start = time.time()
    last_data = time.time()
    buf = b""
    seen_data = False
    while time.time()-start < MAX_SEC:
        d = ser.read_all()
        if d:
            buf += d
            last_data = time.time()
            seen_data = True
            try:
                sys.stdout.write(d.decode("ascii","replace"))
                sys.stdout.flush()
            except Exception:
                pass
        # データ来始めた後、5秒無反応なら終了
        if seen_data and time.time()-last_data > 5.0:
            print("\n[5秒無反応 — 終了]")
            break
        time.sleep(0.05)
    print(f"\n[total {len(buf)} bytes]")
    with open("boot_full.log", "wb") as f: f.write(buf)
    print("saved -> boot_full.log")
