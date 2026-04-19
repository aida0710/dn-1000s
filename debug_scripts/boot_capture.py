# -*- coding: utf-8 -*-
"""起動ログを垂れ流しキャプチャ。login: が出たら止める"""
import serial, time, sys

PORT="COM3"; BAUD=9600
MAX_SEC = 60

with serial.Serial(PORT, BAUD, timeout=0.3) as ser:
    print(f"[capture {MAX_SEC}s — Ctrl-Cで中断]")
    end = time.time()+MAX_SEC
    buf = b""
    last_print = time.time()
    while time.time()<end:
        d = ser.read_all()
        if d:
            buf += d
            try:
                sys.stdout.write(d.decode("ascii","replace"))
                sys.stdout.flush()
            except Exception:
                pass
            # login: が出て、直近1秒で追加出力なければ打ち切り
            if b"login:" in buf[-40:]:
                time.sleep(1.0)
                tail = ser.read_all()
                if not tail:
                    print("\n[login: 検出 -- 終了]")
                    break
                buf += tail
                sys.stdout.write(tail.decode("ascii","replace")); sys.stdout.flush()
        time.sleep(0.05)
    print(f"\n[total {len(buf)}B]")
    with open("boot.log", "wb") as f: f.write(buf)
    print("saved -> boot.log")
