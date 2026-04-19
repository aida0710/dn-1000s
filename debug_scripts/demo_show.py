# -*- coding: utf-8 -*-
"""3色ランプ(赤黄緑)だけでデモ詰め合わせ"""
import time
from dn1000s import DN1000S

dev = DN1000S("192.168.1.150")
RED, YELLOW, GREEN = 1, 2, 3

def all_off():
    dev.acop("00000000")

def flash(n, dur):
    """n番ランプを dur 秒点灯→消灯"""
    dev.lamp_on(n)
    time.sleep(dur)
    dev.lamp_off(n)

def morse_letter(n, code, dot=0.2):
    """モールス文字を点滅 ('.' = 1 dot, '-' = 3 dot, 文字間 3dot, 単位間 1dot)"""
    for c in code:
        if c == ".":
            flash(n, dot)
        elif c == "-":
            flash(n, dot*3)
        time.sleep(dot)  # 要素間

print("[init] 全OFF")
all_off(); time.sleep(0.5)

# ------- 1) SOS モールス (赤) -------
print("\n=== SOS (赤) ===")
for letter in ["...", "---", "..."]:  # S O S
    morse_letter(RED, letter, dot=0.18)
    time.sleep(0.5)  # 文字間
all_off(); time.sleep(1)

# ------- 2) 信号機サイクル -------
print("\n=== 信号機サイクル (緑→黄→赤) ===")
for _ in range(2):
    dev.lamp_on(GREEN); time.sleep(1.5); dev.lamp_off(GREEN)
    dev.lamp_on(YELLOW); time.sleep(0.8); dev.lamp_off(YELLOW)
    dev.lamp_on(RED); time.sleep(1.5); dev.lamp_off(RED)
all_off(); time.sleep(1)

# ------- 3) レインボーチェイス -------
print("\n=== レインボーチェイス ===")
for _ in range(5):
    for n in [RED, YELLOW, GREEN]:
        dev.lamp_on(n); time.sleep(0.15); dev.lamp_off(n)
all_off(); time.sleep(0.5)

# ------- 4) 高速フラッシュ (ACOP一括) -------
print("\n=== 高速フラッシュ (赤+黄+緑同時) ===")
for _ in range(6):
    dev.acop("11100000")  # 赤黄緑 同時ON
    time.sleep(0.15)
    dev.acop("00000000")
    time.sleep(0.15)
time.sleep(0.5)

# ------- 5) 交互点滅 (赤⇔緑) -------
print("\n=== 交互点滅 (赤⇔緑 パトカー風) ===")
for _ in range(8):
    dev.acop("10100000")  # 赤ON 緑ON
    time.sleep(0.25)
    dev.acop("00100000")  # 緑のみ
    time.sleep(0.25)
    dev.acop("10000000")  # 赤のみ
    time.sleep(0.25)
all_off(); time.sleep(0.5)

# ------- 6) フィナーレ: Blink モードで仕上げ -------
print("\n=== フィナーレ: 3色同時 Blink 3秒 ===")
dev.acop("22200000", t=3)  # 2=Blink
time.sleep(4)

all_off()
print("\n[done] お楽しみいただけましたか?")
