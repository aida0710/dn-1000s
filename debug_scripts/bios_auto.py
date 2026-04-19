# -*- coding: utf-8 -*-
"""
電源投入直後にBIOSプロンプトを奪取して情報を引き出す (完全自動)
実行直後から機器の電源を入れること
"""
import serial, time, sys, threading

PORT="COM3"; BAUD=9600

# BIOSで試すコマンド候補 (順番に、応答を全て記録)
BIOS_CMDS = [
    "?",
    "help",
    "h",
    "info",
    "print",
    "printenv",
    "env",
    "show",
    "show config",
    "show net",
    "show ip",
    "show eth0",
    "ifconfig",
    "ifconfig eth0",
    "net",
    "network",
    "version",
    "ver",
    "cat /etc/passwd",
    "cat /etc/shadow",
    "cat /etc/network/interfaces",
    "cat /etc/resolv.conf",
    "cat /etc/hostname",
    "cat /etc/issue",
    "cat /etc/config",
    "ls /etc",
    "ls /",
    "pwd",
    "mem",
    "bootargs",
    "set",
    "setenv",
]

buffer = bytearray()
lock = threading.Lock()

def reader(ser, stop_evt):
    while not stop_evt.is_set():
        d = ser.read_all()
        if d:
            with lock:
                buffer.extend(d)
            try:
                sys.stdout.write(d.decode("ascii","replace")); sys.stdout.flush()
            except Exception:
                pass
        time.sleep(0.03)

def wait_for(needle_bytes, timeout=2.5):
    t = time.time()
    needle = needle_bytes.lower()
    while time.time()-t < timeout:
        with lock:
            if needle in bytes(buffer).lower():
                return True
        time.sleep(0.05)
    return False

def clear_buf():
    with lock:
        buffer.clear()

def main():
    print(f"[*] {PORT}@{BAUD} オープン。すぐに機器の電源を入れてください。")
    with serial.Serial(PORT, BAUD, timeout=0.2) as ser:
        stop = threading.Event()
        t = threading.Thread(target=reader, args=(ser,stop), daemon=True)
        t.start()

        # 起動直後の 30秒間、ESC / Enter / Ctrl-C を連打して BIOS 奪取
        got_bios = False
        t_end = time.time() + 30.0
        while time.time() < t_end and not got_bios:
            for key in [b"\x1b", b"\r", b"\x03", b" "]:
                ser.write(key); time.sleep(0.08)
                with lock:
                    snap = bytes(buffer)
                # BIOS(0)> or BIOS(x)> を検出
                if b"BIOS(" in snap:
                    # プロンプト末尾 '> ' があるまで少し待つ
                    time.sleep(0.4)
                    with lock:
                        snap2 = bytes(buffer)
                    if b"BIOS(" in snap2 and b"> " in snap2.split(b"BIOS(")[-1][:30]:
                        got_bios = True
                        break
        if not got_bios:
            print("\n[!] BIOSを捕獲できませんでした")
            stop.set()
            return

        print("\n\n[*** BIOS確保 — 自動コマンド試行開始 ***]\n")
        time.sleep(0.5)
        # 念のため Enter を送ってプロンプト安定化
        ser.write(b"\r"); time.sleep(0.5)

        results = []
        for cmd in BIOS_CMDS:
            clear_buf()
            print(f"\n----- {cmd!r} -----")
            ser.write(cmd.encode()+b"\r")
            time.sleep(1.2)
            with lock:
                snap = bytes(buffer)
            results.append((cmd, snap))

        print("\n\n[*** 全コマンド完了 ***]")
        with open("bios_dump.log", "wb") as f:
            for cmd, snap in results:
                f.write(f"\n===== {cmd} =====\n".encode())
                f.write(snap)
        print("saved -> bios_dump.log")
        stop.set()

if __name__=="__main__":
    main()
