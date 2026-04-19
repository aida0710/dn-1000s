# -*- coding: utf-8 -*-
"""
LAN内のDN-1000Sを発見する:
 1) 指定セグメントを並列 ping で叩く
 2) arp -a の結果から MAC 00:a0:66:0f:59:52 を検索
 3) 見つかったIPに Telnet(23)/HTTP(80) をプローブ
"""
import subprocess
import concurrent.futures
import re
import socket
import sys

TARGET_MAC = "00-a0-66-0f-59-52"   # Windows arp形式
SUBNETS = ["192.168.1", "192.168.0", "192.168.11", "192.168.10"]

def ping(ip):
    # Windows ping: -n 1 -w 300 (1回、300ms待ち)
    subprocess.run(
        ["ping", "-n", "1", "-w", "300", ip],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=0x08000000 if sys.platform=="win32" else 0,
    )

def sweep(subnet):
    ips = [f"{subnet}.{i}" for i in range(1,255)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as ex:
        list(ex.map(ping, ips))

def arp_table():
    out = subprocess.run(["arp","-a"], capture_output=True, text=True, encoding="cp932").stdout
    rows = []
    for line in out.splitlines():
        m = re.match(r"\s+(\d+\.\d+\.\d+\.\d+)\s+([0-9a-f-]{17})\s+(\S+)", line, re.I)
        if m:
            rows.append((m.group(1), m.group(2).lower()))
    return rows

def probe_port(ip, port, timeout=0.5):
    try:
        with socket.create_connection((ip, port), timeout=timeout) as s:
            s.settimeout(0.5)
            try:
                banner = s.recv(256)
            except Exception:
                banner = b""
            return True, banner
    except Exception as e:
        return False, str(e)

def main():
    print(f"[*] MAC {TARGET_MAC} を探す")
    for sn in SUBNETS:
        print(f"  ping sweep {sn}.0/24 ...")
        sweep(sn)
    rows = arp_table()
    print(f"\n[*] arp -a entries: {len(rows)}")
    hit = None
    for ip,mac in rows:
        marker = " <== TARGET" if mac == TARGET_MAC else ""
        if ip.startswith(("192.168.","10.","172.")):
            print(f"   {ip:15s}  {mac}{marker}")
        if mac == TARGET_MAC:
            hit = ip
    if not hit:
        print("\n[!] 対象MACはARPテーブルに無し。別セグメントの可能性。")
        # それでも 192.168.x.1-254 の開いているTCP23/80を羅列しておく
        print("\n[*] 開いているサービスを広域検索:")
        alive = [ip for ip,_ in rows if ip.startswith(("192.168.0.","192.168.1."))]
        for ip in alive:
            for port in (23,80):
                ok, b = probe_port(ip, port, 0.3)
                if ok:
                    tag = {23:"telnet", 80:"http"}[port]
                    print(f"   {ip}:{port}/{tag}  banner={b[:80]!r}")
        return
    print(f"\n[+] 発見: DN-1000S は {hit} にいる")
    print("\n[*] ポートスキャン:")
    for port in (21, 22, 23, 80, 443, 8080, 8000, 9999, 10000, 30718):
        ok, b = probe_port(hit, port, 0.8)
        print(f"   {hit}:{port} -> {'OPEN' if ok else 'closed'}  {b!r}" if ok else f"   {hit}:{port} -> closed")

if __name__=="__main__":
    main()
