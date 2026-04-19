# -*- coding: utf-8 -*-
"""挙動観察: 無入力/Enter/Ctrl-C/help 等を順に送ってログを取る"""
import serial, time

PORT = "COM3"
BAUD = 9600

def drain(ser, dur):
    end = time.time()+dur; buf=b""
    while time.time()<end:
        d = ser.read_all()
        if d: buf += d
        time.sleep(0.05)
    return buf

with serial.Serial(PORT, BAUD, timeout=0.3) as ser:
    print("=== 0) オープン直後 3秒無入力 ===")
    print(repr(drain(ser, 3.0)))

    print("\n=== 1) \\r のみ ===")
    ser.write(b"\r"); print(repr(drain(ser, 1.5)))

    print("\n=== 2) \\n のみ ===")
    ser.write(b"\n"); print(repr(drain(ser, 1.5)))

    print("\n=== 3) Ctrl-C ===")
    ser.write(b"\x03"); print(repr(drain(ser, 1.5)))

    print("\n=== 4) Ctrl-D ===")
    ser.write(b"\x04"); print(repr(drain(ser, 1.5)))

    print("\n=== 5) help\\r\\n ===")
    ser.write(b"help\r\n"); print(repr(drain(ser, 1.5)))

    print("\n=== 6) ?\\r\\n ===")
    ser.write(b"?\r\n"); print(repr(drain(ser, 1.5)))

    print("\n=== 7) root + Enter だけ (passwd 待ち観察) ===")
    ser.write(b"root\r"); print(repr(drain(ser, 3.0)))

    print("\n=== 8) 何もせず 5秒待つ (自発的送信あるか) ===")
    print(repr(drain(ser, 5.0)))
