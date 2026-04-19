# -*- coding: utf-8 -*-
"""ブザーを連続的に鳴らしっぱなしにして物理音量調整を試せるスクリプト
 Ctrl-C で停止 → 全OFF"""
import time, signal, sys
from dn1000s import DN1000S

dev = DN1000S("192.168.1.150")

def cleanup(*_):
    print("\n[停止] 全OFF")
    dev.acop("00000000")
    sys.exit(0)
signal.signal(signal.SIGINT, cleanup)

print("=== ブザー連続ON (4桁目=1) ===")
print("本体のボリュームつまみを探して回してみてください")
print("Ctrl-C で停止")
print()

# 連続ブザーを永続ON (タイマー無しだと自動OFFしないはず)
dev.acop("00010000")

start = time.time()
while True:
    # 10秒ごとに ACOP を再送して自動OFFを防ぐ
    time.sleep(8)
    dev.acop("00010000")
    elapsed = int(time.time() - start)
    print(f"  経過 {elapsed}秒 — 聞こえましたか?")
