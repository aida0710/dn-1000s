# -*- coding: utf-8 -*-
"""
一気通貫: ポートを1度だけ開き、
 (1) 現状のバッファを吸い出し
 (2) 各種刺激を与えて応答をログ
 (3) login: 検出時はデフォルトID/PW総当たり
 (4) 特殊コマンドの試行 (DN1000プロトコル推定)
"""
import serial, time, sys

PORT="COM3"; BAUD=9600

CREDS = [
    ("root",""), ("root","root"), ("root","isa"), ("root","keiko"),
    ("root","admin"), ("root","password"), ("root","dn1000"),
    ("root","dn-1000"), ("root","dn1000s"), ("root","1234"),
    ("root","0000"), ("root","9999"),
    ("admin","admin"), ("admin","password"), ("admin","isa"),
    ("admin","keiko"), ("admin",""), ("admin","1234"),
    ("keiko","keiko"), ("isa","isa"), ("user","user"),
    ("guest","guest"), ("guest",""),
    ("manager","manager"),
]

# 警子ちゃん系でありがちな制御コマンド推定
CMDS = [
    b"\r\n", b"?\r\n", b"help\r\n", b"HELP\r\n", b"VER\r\n", b"ver\r\n",
    b"STATUS\r\n", b"status\r\n", b"RESET\r\n", b"PW\r\n", b"PASS\r\n",
    b"INIT\r\n", b"CONFIG\r\n", b"\x1b", b"\x03", b"\x04",
    b"\x1b[A",  # ↑キー
]

def drain(ser, dur):
    end=time.time()+dur; buf=b""
    while time.time()<end:
        d=ser.read_all()
        if d: buf+=d
        time.sleep(0.05)
    return buf

def printable(b):
    return b.decode("ascii","replace").replace("\r","\\r").replace("\n","\\n")

def main():
    log_lines = []
    def L(s):
        print(s); log_lines.append(s)

    with serial.Serial(PORT, BAUD, timeout=0.3) as ser:
        L("=== STAGE A: 起動直後バッファ吸出し 4秒 ===")
        initial = drain(ser, 4.0)
        L(f"  len={len(initial)}")
        L(f"  tail300={printable(initial[-300:])}")

        L("\n=== STAGE B: コマンド刺激 ===")
        responses = {}
        for c in CMDS:
            ser.reset_input_buffer()
            ser.write(c)
            resp = drain(ser, 1.0)
            responses[c]=resp
            L(f"  send={printable(c):30s} resp={printable(resp)[:200]}")
            time.sleep(0.2)

        L("\n=== STAGE C: Enter を連打してログインプロンプト誘発 ===")
        for _ in range(5):
            ser.write(b"\r\n"); time.sleep(0.2)
        after_enter = drain(ser, 2.0)
        L(f"  after5xEnter: {printable(after_enter)[-300:]}")

        if b"login:" in after_enter.lower():
            L("\n=== STAGE D: login: 検出 → 認証総当たり ===")
            for i,(u,p) in enumerate(CREDS,1):
                ser.write(b"\r\n"); time.sleep(0.3); drain(ser,0.2)
                ser.write(b"\r\n")
                buf=b""; t0=time.time()
                while time.time()-t0<1.5:
                    d=ser.read_all()
                    if d: buf+=d
                    if b"login:" in buf.lower(): break
                    time.sleep(0.05)
                if b"login:" not in buf.lower():
                    L(f"  [{i}] login:プロンプト喪失 buf={printable(buf)[-100:]}")
                    continue
                ser.write(u.encode()+b"\r\n")
                buf=b""; t0=time.time()
                while time.time()-t0<2.0:
                    d=ser.read_all()
                    if d: buf+=d
                    if b"password:" in buf.lower() or b"#" in buf or b"$" in buf or b">" in buf:
                        break
                    if b"login:" in buf.lower() and len(buf)>len(u)+5: break
                    time.sleep(0.05)
                if b"password:" not in buf.lower():
                    if b"#" in buf or b"$" in buf or b">" in buf:
                        L(f"  *** HIT: {u} (no password) ***")
                        L(f"     {printable(buf)[-200:]}")
                        break
                    L(f"  [{i}] {u}/{p!r} -> no Password: prompt. buf={printable(buf)[-100:]}")
                    continue
                ser.write(p.encode()+b"\r\n")
                time.sleep(1.2)
                resp = drain(ser,0.8)
                if b"incorrect" in resp.lower() or b"fail" in resp.lower() or b"invalid" in resp.lower() or b"login:" in resp.lower():
                    L(f"  [{i}] {u}/{p!r} -> FAIL: {printable(resp)[-100:]}")
                elif b"#" in resp or b"$" in resp or b">" in resp:
                    L(f"  *** HIT: {u}/{p!r} ***")
                    L(f"     {printable(resp)[-200:]}")
                    break
                else:
                    L(f"  [{i}] {u}/{p!r} -> ???: {printable(resp)[-120:]}")
        else:
            L("\n  login: 未検出 — 別経路調査が必要")

    with open("all_in_one.log", "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    print("\nsaved -> all_in_one.log")

if __name__=="__main__":
    main()
