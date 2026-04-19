# -*- coding: utf-8 -*-
"""
DN-1000S (警子ちゃんミニ) Linuxコンソール ログイン試行
9600bps でログインプロンプトが確認済み。
典型的なデフォルトID/PWを試す。
"""
import serial
import time
import sys

PORT = "COM3"
BAUD = 9600

CREDS = [
    ("root", ""),
    ("root", "root"),
    ("root", "isa"),
    ("root", "keiko"),
    ("root", "admin"),
    ("root", "password"),
    ("root", "dn-1000s"),
    ("root", "dn1000s"),
    ("root", "1234"),
    ("root", "0000"),
    ("root", "9999"),
    ("admin", "admin"),
    ("admin", "password"),
    ("admin", "isa"),
    ("admin", "keiko"),
    ("admin", ""),
    ("keiko", "keiko"),
    ("keiko", "isa"),
    ("isa", "isa"),
    ("user", "user"),
    ("guest", "guest"),
    ("guest", ""),
    ("sh", ""),
]


def drain(ser, dur=0.3):
    end = time.time() + dur
    buf = b""
    while time.time() < end:
        d = ser.read_all()
        if d:
            buf += d
        time.sleep(0.05)
    return buf


def wait_for(ser, needle, timeout=3.0):
    buf = b""
    end = time.time() + timeout
    while time.time() < end:
        d = ser.read_all()
        if d:
            buf += d
            if needle in buf.lower():
                return buf
        time.sleep(0.05)
    return buf


def try_login(ser, user, pw):
    # 一度 Enter で状態リセット
    ser.write(b"\r\n")
    time.sleep(0.3)
    drain(ser, 0.3)
    ser.write(b"\r\n")
    buf = wait_for(ser, b"login:", 2.0)
    if b"login:" not in buf.lower():
        return False, buf
    ser.write(user.encode() + b"\r\n")
    buf = wait_for(ser, b"password:", 2.0)
    if b"password:" not in buf.lower():
        # パスワード無しユーザーでシェルに入った可能性
        more = drain(ser, 0.8)
        return (b"#" in more or b"$" in more or b">" in more), buf + more
    ser.write(pw.encode() + b"\r\n")
    time.sleep(1.0)
    resp = drain(ser, 1.2)
    if b"incorrect" in resp.lower() or b"failure" in resp.lower() or b"login:" in resp.lower():
        return False, resp
    if b"#" in resp or b"$" in resp or b">" in resp:
        return True, resp
    return False, resp


def main():
    print(f"=== DN-1000S ログイン試行 ({PORT} @ {BAUD}) ===")
    with serial.Serial(PORT, BAUD, timeout=0.3) as ser:
        # バナー読み飛ばし
        time.sleep(0.5)
        banner = drain(ser, 1.0)
        print(f"初期バッファ(tail 200b): {banner[-200:]!r}")
        print()
        for i, (u, p) in enumerate(CREDS, 1):
            print(f"[{i}/{len(CREDS)}] {u} / {p!r} ...", end=" ", flush=True)
            ok, resp = try_login(ser, u, p)
            tail = resp[-120:] if resp else b""
            print(("HIT!!" if ok else "miss"), f"resp={tail!r}")
            if ok:
                print()
                print(f"*** 認証成功: {u} / {p!r} ***")
                # 簡易情報取得
                for cmd in [b"id\r\n", b"uname -a\r\n", b"cat /etc/issue\r\n"]:
                    ser.write(cmd)
                    time.sleep(0.8)
                    print(f"  {cmd.strip().decode()}: {drain(ser, 0.6)!r}")
                return
            time.sleep(0.3)
        print()
        print("すべての既定の組み合わせが失敗しました")


if __name__ == "__main__":
    main()
