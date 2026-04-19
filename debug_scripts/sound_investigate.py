# -*- coding: utf-8 -*-
"""音関連コマンドのヘルプと実動作を調査"""
import time
from dn1000s import DN1000S

dev = DN1000S("192.168.1.150")

print("=== HELP per command ===")
for c in ["ROPS", "SDEF", "RLY4", "RLY5", "RLY6", "RLY7", "RLY8", "ACOP", "SPOP", "SNDV", "VOL"]:
    print(f"\n>>> HELP {c}")
    r = dev._rsh(f"HELP {c}")
    print(r)

print("\n=== ROPS (no args) ===")
print(dev._rsh("ROPS"))

print("\n=== SDEF (no args) ===")
print(dev._rsh("SDEF"))

# RLY4-8を引数無しで叩いて現在状態を見る (機器が持っているリレー数が分かる)
print("\n=== RLY4-8 現在状態 ===")
for n in range(4, 9):
    r = dev._rsh(f"RLY{n}")
    print(f"RLY{n}: {r!r}")
