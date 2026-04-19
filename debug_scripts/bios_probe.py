# -*- coding: utf-8 -*-
"""BIOS(0)> プロンプトに対して各種コマンドを投げて応答を見る"""
import serial, time, sys

PORT="COM3"; BAUD=9600

CMDS = [
    b"?\r",
    b"help\r",
    b"h\r",
    b"HELP\r",
    b"version\r",
    b"ver\r",
    b"printenv\r",
    b"print\r",
    b"env\r",
    b"setenv\r",
    b"set\r",
    b"ls\r",
    b"dir\r",
    b"info\r",
    b"show\r",
    b"status\r",
    b"boot\r",
    b"bootm\r",
    b"bootargs\r",
    b"run\r",
    b"reset\r",
    b"reboot\r",
    b"mem\r",
    b"md\r",
    b"passwd\r",
    b"password\r",
    b"users\r",
]

def drain(ser, dur):
    end=time.time()+dur; buf=b""
    while time.time()<end:
        d=ser.read_all()
        if d: buf+=d
        time.sleep(0.05)
    return buf

with serial.Serial(PORT, BAUD, timeout=0.3) as ser:
    print("[*] 現状バッファ:")
    print(repr(drain(ser, 1.0)))
    print()
    # プロンプト誘発
    ser.write(b"\r"); time.sleep(0.3); print(repr(drain(ser,0.5)))
    print()
    print("=== コマンド試行 ===")
    for c in CMDS:
        ser.write(c)
        resp = drain(ser, 1.2)
        tag = c.strip().decode()
        # BIOS(0)> 部分を除去して本体だけ見る
        print(f"\n>>> {tag}")
        try:
            text = resp.decode("ascii","replace")
        except Exception:
            text = repr(resp)
        print(text if text.strip() else "(応答無しまたはエコーのみ)")
        time.sleep(0.15)
    print("\n=== 完了 ===")
