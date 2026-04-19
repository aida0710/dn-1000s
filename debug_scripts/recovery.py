# -*- coding: utf-8 -*-
"""
EEPROM誤クリア後の復旧: BIOSのConfig Menuに正しい値を入力する
- MAC は初回ブートログで判明した 00:A0:66:0F:59:52 を復元
- IP は 192.168.1.150 (ユーザーLANで空き)
- Gateway は 192.168.1.1 (実ゲートウェイ)
"""
import serial, time, sys, threading, re

PORT = "COM3"
BAUD = 9600

# ★ 復元する値
TARGET_IP = "192.168.1.150"
GATEWAY   = "192.168.1.1"
NETMASK   = "255.255.255.0"
TFTP_IP   = "192.168.1.250"      # factory default (使わないがこのまま)
TFTP_FILE = "c:\\tftp\\firm"     # factory default
MAC       = "00:A0:66:0F:59:52"  # 初回ログで判明した元のMAC

def reader(ser, buf, stop):
    while not stop.is_set():
        d = ser.read_all()
        if d:
            buf.append(d)
            try:
                sys.stdout.write(d.decode("ascii","replace"))
                sys.stdout.flush()
            except Exception:
                pass
        time.sleep(0.03)

def snap(buf):
    return b"".join(buf)

def wait_for(buf, pattern, timeout=15):
    pat = re.compile(pattern if isinstance(pattern, bytes) else pattern.encode())
    t = time.time()
    while time.time()-t < timeout:
        if pat.search(snap(buf)):
            return True
        time.sleep(0.05)
    return False

def main():
    print(f"[recovery] {PORT}@{BAUD} オープン")
    print(f"  復元MAC: {MAC}")
    print(f"  復元IP : {TARGET_IP} / GW {GATEWAY}\n")
    print(">>> 機器の電源を入れてください <<<\n")

    with serial.Serial(PORT, BAUD, timeout=0.2) as ser:
        buf = []
        stop = threading.Event()
        t = threading.Thread(target=reader, args=(ser,buf,stop), daemon=True)
        t.start()

        # 1) まず無干渉で10秒待機 — EEPROMが全ゼロなら自動で Config menu が出るかも
        print("[1] 10秒無干渉待機 (config menu自動表示期待)...")
        if wait_for(buf, r"IP Address \[", timeout=12):
            print("\n[+] Config menu 自動表示を検出")
        else:
            # 2) 出なかったら Ctrl-C を1回だけ送って誘発
            print("\n[2] Config menu 未表示 → Ctrl-C で誘発試行")
            ser.write(b"\x03")
            if not wait_for(buf, r"IP Address \[", timeout=12):
                # 3) BIOSプロンプトに入ったかも、その場合はBIOSから手動設定
                if b"BIOS(" in snap(buf):
                    print("\n[!] BIOSプロンプトで停止。BIOSコマンドで修復を試みる")
                    ser.write(b"?\r"); time.sleep(1.5)
                    ser.write(b"help\r"); time.sleep(1.5)
                    time.sleep(3)
                print("\n[!] Config menu に到達できず。停止。")
                stop.set()
                return

        # 各プロンプトに返答
        def respond(pattern, value, label):
            print(f"\n[>] {label}: 送信='{value}'")
            if not wait_for(buf, pattern, timeout=8):
                print(f"[!] プロンプト '{pattern}' 未検出")
                return False
            time.sleep(0.5)
            ser.write(value.encode() + b"\r")
            time.sleep(0.4)
            return True

        # IP Address はすでに検出済み — そのまま送信
        time.sleep(0.5)
        ser.write(TARGET_IP.encode() + b"\r"); time.sleep(0.5)
        print(f"\n[>] IP Address 送信: {TARGET_IP}")

        respond(r"Gateway IP \[",      GATEWAY,   "Gateway IP")
        respond(r"Subnet Mask \[",     NETMASK,   "Subnet Mask")
        respond(r"TFTP Server IP \[",  TFTP_IP,   "TFTP Server IP")
        respond(r"TFTP Boot File \[",  TFTP_FILE, "TFTP Boot File")
        respond(r"Ethernet Address \[", MAC,      "Ethernet Address (★MAC復元★)")

        # 書き込み完了待ち
        print("\n[*] EEPROM書込み完了を待機...")
        wait_for(buf, r"Write system parameters.*Done", timeout=10)

        # ブート継続観察
        print("\n[*] ブート完了まで 30秒観察...")
        time.sleep(30)

        final = snap(buf).decode("ascii","replace")
        # eth0 ラインを確認
        print("\n\n=== 観察まとめ ===")
        for line in final.split("\n"):
            if "eth0" in line or "IP Address" in line or "Ethernet Address" in line:
                print("  ", line.strip())

        stop.set()

if __name__ == "__main__":
    main()
