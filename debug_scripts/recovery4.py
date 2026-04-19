# -*- coding: utf-8 -*-
"""
v4: IPアドレス格納のズレを修正
 - ESC送信は検出前にチェック (余剰ESCを送らない)
 - Config検出後にバックスペース+待機で入力バッファ浄化
 - Enter前のドレインで残留ESCを確実に消費
"""
import serial, time, sys, threading, re

PORT="COM3"; BAUD=9600
TARGET_IP="192.168.1.150"; GATEWAY="192.168.1.1"; NETMASK="255.255.255.0"
TFTP_IP="192.168.1.250"; TFTP_FILE="c:\\tftp\\firm"
MAC="00:A0:66:0F:59:52"

buf=bytearray(); lock=threading.Lock()

def reader(ser, stop):
    while not stop.is_set():
        d=ser.read_all()
        if d:
            with lock: buf.extend(d)
            try: sys.stdout.write(d.decode("ascii","replace")); sys.stdout.flush()
            except: pass
        time.sleep(0.02)

def snap():
    with lock: return bytes(buf)

def wait_for(pat, timeout=10):
    p=re.compile(pat.encode() if isinstance(pat,str) else pat)
    t0=time.time()
    while time.time()-t0<timeout:
        if p.search(snap()): return True
        time.sleep(0.03)
    return False

def send_value(ser, value, label):
    # バックスペースで入力バッファを浄化 → 少し待つ → 値送信
    time.sleep(0.3)
    ser.write(b"\x08"*20)  # BS連打で既存入力クリア
    time.sleep(0.3)
    ser.write(value.encode()+b"\r")
    time.sleep(0.4)
    print(f"[>] {label}: {value}")

def main():
    print(f"[recovery4] ESC連打v4 — 電源投入してください")
    with serial.Serial(PORT, BAUD, timeout=0.2) as ser:
        stop=threading.Event()
        t=threading.Thread(target=reader,args=(ser,stop),daemon=True); t.start()

        # フェーズ1: 検出優先ループ
        print("[phase1] ESC連打(検出優先)...")
        t_end=time.time()+25
        got=False
        while time.time()<t_end:
            # まず検出
            s=snap()
            if b"IP Address [" in s:
                got=True; print("\n[+] Config menu 検出 (IP Addressプロンプト)")
                break
            if b"Starting autoboot" in s or b"Uncompressing Linux" in s:
                print("\n[!] autoboot失敗"); stop.set(); return
            # 検出しなかったらESC送信
            ser.write(b"\x1b")
            time.sleep(0.1)

        if not got:
            print("\n[!] Config menu 未検出"); stop.set(); return

        # 超重要: 送信中だったESCが全部デバイスに届くのを待つ
        # そして IP Address プロンプト末尾の ">" まで出終わるのを待つ
        print("[*] 1.5秒ドレイン待機 (残留ESC消化)")
        time.sleep(1.5)

        # フェーズ2: 各プロンプトに値入力 (BSで浄化してから値)
        print("\n[phase2] 設定値入力")
        send_value(ser, TARGET_IP, "IP Address")

        wait_for(r"Gateway IP \[",8); send_value(ser, GATEWAY, "Gateway IP")
        wait_for(r"Subnet Mask \[",8); send_value(ser, NETMASK, "Subnet Mask")
        wait_for(r"TFTP Server IP \[",8); send_value(ser, TFTP_IP, "TFTP Server IP")
        wait_for(r"TFTP Boot File \[",8); send_value(ser, TFTP_FILE, "TFTP Boot File")
        wait_for(r"Ethernet Address \[",8); send_value(ser, MAC, "Ethernet Address")

        wait_for(r"Write system parameters.*Done",10)
        print("\n[+] 書込完了。50秒ブート観察")
        time.sleep(50)

        final=snap().decode("ascii","replace")
        with open("recovery4.log", "w", encoding="utf-8") as f: f.write(final)

        # System Configuration Table を抽出して検証
        print("\n=== 最終確認 ===")
        m=re.search(r"System Configuration Table.+?\+====+\+", final, re.S)
        if m:
            print(m.group(0))
        else:
            print("(table not found)")
        for L in final.split("\n"):
            if "eth0" in L and "66" in L: print("  kernel eth0:", L.strip())

        stop.set()

if __name__=="__main__": main()
