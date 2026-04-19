# -*- coding: utf-8 -*-
"""
改良版v3: ESC 単体を連打して Config Menu を誘発
検出したら正しい値を入力
"""
import serial, time, sys, threading, re

PORT="COM3"; BAUD=9600
TARGET_IP="192.168.1.150"; GATEWAY="192.168.1.1"; NETMASK="255.255.255.0"
TFTP_IP="192.168.1.250"; TFTP_FILE="c:\\tftp\\firm"
MAC="00:A0:66:0F:59:52"

buf = bytearray(); lock = threading.Lock()

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

def wait_for(pat, timeout=15):
    p = re.compile(pat.encode() if isinstance(pat,str) else pat)
    t0=time.time()
    while time.time()-t0<timeout:
        if p.search(snap()): return True
        time.sleep(0.03)
    return False

def send_line(ser, s):
    ser.write(s.encode()+b"\r"); time.sleep(0.4)

def main():
    print(f"[recovery3] ESC連打モード — 電源投入してください")
    with serial.Serial(PORT, BAUD, timeout=0.2) as ser:
        stop=threading.Event()
        t=threading.Thread(target=reader,args=(ser,stop),daemon=True); t.start()

        # ESC のみを 100ms 毎に送信、最大20秒
        print("[phase1] ESC連打中...")
        t_end=time.time()+20
        got=False
        while time.time()<t_end:
            ser.write(b"\x1b"); time.sleep(0.1)
            s=snap()
            if b"Configure the System" in s or b"IP Address [" in s:
                got=True; print("\n[+] Config menu 検出")
                break
            if b"Starting autoboot" in s or b"Uncompressing Linux" in s:
                print("\n[!] autoboot — 失敗"); stop.set(); return

        if not got:
            print("\n[!] ESC連打 → Config menu 出ず")
            # BIOS(0)> が見えたか確認
            if b"BIOS(" in snap():
                print("[*] BIOSプロンプトは出た。BIOSコマンド試行可能")
                # BIOS autoboot を止めるため Enter を送ってコマンド試行
                ser.write(b"\r"); time.sleep(0.5)
                # BIOS で使えるか不明なコマンドをいくつか
                for c in ["config","setup","init"]:
                    ser.write(c.encode()+b"\r"); time.sleep(1.2)
            stop.set(); return

        # Config Menu が出たので値を入れる
        print("\n[phase2] 設定値入力")
        time.sleep(0.5)
        send_line(ser, TARGET_IP); print(f"[>] IP={TARGET_IP}")
        wait_for(r"Gateway IP \[",8); send_line(ser,GATEWAY); print(f"[>] GW={GATEWAY}")
        wait_for(r"Subnet Mask \[",8); send_line(ser,NETMASK); print(f"[>] NM={NETMASK}")
        wait_for(r"TFTP Server IP \[",8); send_line(ser,TFTP_IP); print(f"[>] TFTP={TFTP_IP}")
        wait_for(r"TFTP Boot File \[",8); send_line(ser,TFTP_FILE); print(f"[>] TFTPF={TFTP_FILE}")
        wait_for(r"Ethernet Address \[",8); send_line(ser,MAC); print(f"[>] MAC={MAC}")

        wait_for(r"Write system parameters.*Done",10)
        print("\n[+] 書込完了。40秒ブート観察")
        time.sleep(40)

        final = snap().decode("ascii","replace")
        with open("recovery3.log", "w", encoding="utf-8") as f: f.write(final)
        print("\n=== eth0 line ===")
        for L in final.split("\n"):
            if "eth0" in L or "login:" in L: print("  ", L.strip())
        stop.set()

if __name__=="__main__": main()
