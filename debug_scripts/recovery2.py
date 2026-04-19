# -*- coding: utf-8 -*-
"""
改良版: 電源ON直後から Ctrl-C 連打で Config menu を強制誘発
検出したら即停止し、各プロンプトに正しい値を返す
"""
import serial, time, sys, threading, re

PORT="COM3"; BAUD=9600

TARGET_IP = "192.168.1.150"
GATEWAY   = "192.168.1.1"
NETMASK   = "255.255.255.0"
TFTP_IP   = "192.168.1.250"
TFTP_FILE = "c:\\tftp\\firm"
MAC       = "00:A0:66:0F:59:52"

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

def snap():
    with lock: return bytes(buf)

def wait_for(pat, timeout=20):
    p = re.compile(pat if isinstance(pat, bytes) else pat.encode())
    t0 = time.time()
    while time.time()-t0 < timeout:
        if p.search(snap()): return True
        time.sleep(0.03)
    return False

def send_line(ser, s):
    ser.write(s.encode() + b"\r")
    time.sleep(0.4)

def main():
    print(f"[recovery2] {PORT}@{BAUD} — 機器の電源を入れてください\n")
    with serial.Serial(PORT, BAUD, timeout=0.2) as ser:
        stop = threading.Event()
        t = threading.Thread(target=reader, args=(ser,stop), daemon=True); t.start()

        # フェーズ1: 電源投入検知 + Ctrl-C連打
        # 最大20秒、0.1秒ごとに \x03 を送る、"Configure the System" か "BIOS(" を検出したら止める
        print("[phase1] Ctrl-C 連打で Config menu 誘発試行...")
        t_end = time.time() + 25
        got_config = False
        while time.time() < t_end:
            ser.write(b"\x03")
            time.sleep(0.1)
            s = snap()
            if b"Configure the System" in s or b"IP Address [" in s:
                got_config = True
                print("\n[+] Config menu 検出!")
                break
            if b"Starting autoboot" in s or b"Uncompressing Linux" in s:
                print("\n[!] autobootに入ってしまった — リセットが必要")
                stop.set(); return

        if not got_config:
            print("\n[!] Config menu に入れず")
            stop.set(); return

        # フェーズ2: 各プロンプトに値を入れる
        print("\n[phase2] プロンプトに応答")

        # IP Address は既に検出済み
        time.sleep(0.5)
        send_line(ser, TARGET_IP); print(f"[>] IP: {TARGET_IP}")

        wait_for(r"Gateway IP \[", 8);  send_line(ser, GATEWAY);   print(f"[>] GW: {GATEWAY}")
        wait_for(r"Subnet Mask \[", 8); send_line(ser, NETMASK);   print(f"[>] NM: {NETMASK}")
        wait_for(r"TFTP Server IP \[", 8); send_line(ser, TFTP_IP); print(f"[>] TFTP IP: {TFTP_IP}")
        wait_for(r"TFTP Boot File \[", 8); send_line(ser, TFTP_FILE); print(f"[>] TFTP file: {TFTP_FILE}")
        wait_for(r"Ethernet Address \[", 8); send_line(ser, MAC);   print(f"[>] MAC: {MAC}")

        # 書き込み確認
        wait_for(r"Write system parameters.*Done", 10)
        print("\n[+] 書き込み完了")

        # あとは BIOS(0)> が出るが、autoboot に任せて起動を観察
        print("\n[observe] 起動完了まで40秒観察")
        time.sleep(40)

        final = snap().decode("ascii","replace")
        with open("recovery2.log","w",encoding="utf-8") as f:
            f.write(final)
        print("\n=== eth0 / ネットワーク関連行 ===")
        for line in final.split("\n"):
            L = line.strip()
            if any(k in L for k in ["eth0", "IP Address", "Ethernet Address", "ifconfig", "Gateway", "Subnet"]):
                print("  ", L)
        stop.set()

if __name__=="__main__":
    main()
