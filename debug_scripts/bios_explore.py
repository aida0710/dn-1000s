# -*- coding: utf-8 -*-
"""BIOS(0)> プロンプトで止まった状態から各種コマンドを試行"""
import serial, time, sys, threading

PORT="COM3"; BAUD=9600

# 手当たり次第
CMDS = [
    # ヘルプ系
    "h", "help", "H", "HELP", "?", "??", ".", "/",
    # 設定系
    "config", "cfg", "setup", "init", "initialize", "initial",
    "reset", "clear", "default", "defaults", "factory",
    # 表示系
    "show", "info", "ver", "version", "list", "print", "status",
    # ネットワーク系
    "net", "network", "ifconfig", "ip", "mac", "eth0",
    # メモリ/EEPROM系
    "mem", "md", "mw", "ee", "eeprom", "write", "read", "save",
    # 単独文字
    "a", "b", "c", "d", "e", "i", "l", "n", "p", "q", "r", "s", "t", "w", "x",
    # 数字メニュー
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    # コマンド系
    "boot", "go", "start", "run",
]

buf = bytearray()
lock = threading.Lock()

def reader(ser, stop):
    while not stop.is_set():
        d = ser.read_all()
        if d:
            with lock: buf.extend(d)
            try: sys.stdout.write(d.decode("ascii","replace")); sys.stdout.flush()
            except: pass
        time.sleep(0.02)

def drain_and_ret(dur):
    time.sleep(dur)
    with lock:
        data = bytes(buf); buf.clear()
    return data

def main():
    with serial.Serial(PORT, BAUD, timeout=0.2) as ser:
        stop = threading.Event()
        t = threading.Thread(target=reader, args=(ser,stop), daemon=True); t.start()

        # まず現状確認 (BIOS(0)>で止まっているはず)
        print("[*] 現状確認 2秒...")
        init = drain_and_ret(2.0)
        print(f"\n[init snapshot tail]: {init[-200:]!r}")

        # プロンプトを誘発
        ser.write(b"\r"); time.sleep(0.5)
        state = drain_and_ret(0.3)
        if b"BIOS(" not in state and b">" not in state:
            print(f"[!] BIOSプロンプト状態ではない: {state!r}")
            # 保険でCtrl-Cも
            ser.write(b"\x03"); time.sleep(0.3)
            ser.write(b"\r"); time.sleep(0.5)
            print(f"[retry] {drain_and_ret(0.3)!r}")

        results = []
        for cmd in CMDS:
            ser.write(cmd.encode()+b"\r")
            resp = drain_and_ret(0.8)
            # エコーを除去して意味ある応答かチェック
            tag = cmd
            text = resp.decode("ascii","replace")
            interesting = ("error" not in text.lower() and len(text.strip()) > len(cmd)+3)
            marker = " <-- 注目!" if interesting else ""
            print(f"\n>>> {tag!r}{marker}\n{text.rstrip()}")
            results.append((cmd, text))

        with open("bios_explore.log", "w", encoding="utf-8") as f:
            for c,r in results:
                f.write(f"\n===== {c} =====\n{r}\n")
        print("\nsaved -> bios_explore.log")
        stop.set()

if __name__=="__main__":
    main()
