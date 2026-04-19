# -*- coding: utf-8 -*-
"""RLY1-8 を順番に点灯して、何がどれに対応するか見てマップする"""
import time
from dn1000s import DN1000S

dev = DN1000S("192.168.1.150")

# 全部OFFで初期化
print("[init] 全リレーOFF")
dev.acop("00000000")
time.sleep(1)

for n in range(1, 9):
    print(f"\n>>> RLY{n} を 2.5秒点灯します。何が光った/鳴ったか観察してください")
    dev.lamp_on(n, t=2)
    time.sleep(2.8)
    # 念のためOFF
    dev.lamp_off(n)
    time.sleep(0.3)

print("\n[done] 結果を教えてください:")
print("  RLY1 = ?")
print("  RLY2 = ?")
print("  ... (例: RLY1=赤, RLY2=黄, RLY3=緑, RLY4=ブザー連続, RLY5=ブザー断続…)")
