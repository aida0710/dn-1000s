# -*- coding: utf-8 -*-
"""ACOP の4桁目・5桁目をONにして、ブザーが鳴るか試す"""
import time
from dn1000s import DN1000S

dev = DN1000S("192.168.1.150")

print("[init] 全OFF"); dev.acop("00000000"); time.sleep(1)

patterns = [
    ("00010000", "4桁目=1 (連続ブザー?) 2秒"),
    ("00001000", "5桁目=1 (断続ブザー?) 2秒"),
    ("00020000", "4桁目=2 (Blink) 2秒"),
    ("00002000", "5桁目=2 (Blink) 2秒"),
    ("00000100", "6桁目=1 2秒"),
    ("00000010", "7桁目=1 2秒"),
    ("00000001", "8桁目=1 2秒"),
    ("00011000", "連続+断続同時 2秒"),
]

for pat, desc in patterns:
    print(f"\n>>> ACOP {pat}  -- {desc}")
    r = dev.acop(pat)
    print(f"   応答: {r!r}")
    time.sleep(2.2)
    dev.acop("00000000")
    time.sleep(0.8)

# ROPS も試す (8桁出た)
print("\n=== ROPS 試行 ===")
for pat in ["10000000","00010000","00001000","11111000"]:
    print(f">>> ROPS {pat}")
    r = dev._rsh(f"ROPS {pat}")
    print(f"   応答: {r!r}")
    time.sleep(1.5)
    dev._rsh("ROPS 00000000")
    time.sleep(0.5)

# monitor.cgi を叩いて現在状態を確認
import http.client, socket
conn=http.client.HTTPConnection("192.168.1.150",80,timeout=5)
conn.request("GET","/cgi-bin/monitor.cgi?stat=1")
s=conn.sock; s.settimeout(3); d=b""
try:
    while True:
        c=s.recv(4096)
        if not c: break
        d+=c
        if len(d)>65536: break
except: pass
conn.close()
if d.startswith(b"HTTP/"): d = d[d.find(b"\r\n\r\n")+4:]
text = d.decode("shift_jis","replace")
import re
print("\n=== monitor.cgi の各項目状態 ===")
# alt='xxx' と直前のラベル (BLUE>(label)) を対応させる
for m in re.finditer(r"FONT COLOR=BLUE>([^<]+)</FONT>.*?alt='([^']+)'", text, re.S):
    label = m.group(1).replace("<br>","/").replace("<BR>","/")
    alt = m.group(2)
    print(f"  {label} -> {alt}")
