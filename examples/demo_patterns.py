# -*- coding: utf-8 -*-
"""
使えるパターンのライブラリ。関数として import して使うのもOK
  python demo_patterns.py signal    # 信号機
  python demo_patterns.py sos       # SOS
  python demo_patterns.py rainbow   # レインボーチェイス
  python demo_patterns.py police    # パトカー風
"""
import time, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from debug_scripts.dn1000s import DN1000S


def signal_cycle(dev, n=2):
    """信号機: 緑→黄→赤 を n 回"""
    for _ in range(n):
        dev.green.on();  time.sleep(1.5); dev.green.off()
        dev.yellow.on(); time.sleep(0.7); dev.yellow.off()
        dev.red.on();    time.sleep(1.5); dev.red.off()


def morse(dev, text, dot=0.18, channel_name="red"):
    """文字列をモールス信号で点滅"""
    table = {
        "A":".-",    "B":"-...",  "C":"-.-.",  "D":"-..",   "E":".",
        "F":"..-.",  "G":"--.",   "H":"....",  "I":"..",    "J":".---",
        "K":"-.-",   "L":".-..",  "M":"--",    "N":"-.",    "O":"---",
        "P":".--.",  "Q":"--.-",  "R":".-.",   "S":"...",   "T":"-",
        "U":"..-",   "V":"...-",  "W":".--",   "X":"-..-",  "Y":"-.--",
        "Z":"--..",
        "0":"-----", "1":".----", "2":"..---", "3":"...--", "4":"....-",
        "5":".....", "6":"-....", "7":"--...", "8":"---..", "9":"----.",
    }
    ch = getattr(dev, channel_name)
    for c in text.upper():
        code = table.get(c, "")
        if not code:
            time.sleep(dot * 7)  # 単語間
            continue
        for symbol in code:
            ch.on()
            time.sleep(dot if symbol == "." else dot * 3)
            ch.off()
            time.sleep(dot)      # 要素間
        time.sleep(dot * 3)      # 文字間


def rainbow_chase(dev, times=10, speed=0.12):
    """赤→黄→緑 を高速で順送り"""
    colors = [dev.red, dev.yellow, dev.green]
    for _ in range(times):
        for c in colors:
            c.on(); time.sleep(speed); c.off()


def police(dev, times=10):
    """パトカー風の赤⇔黄点滅"""
    for _ in range(times):
        dev.acop("10000000"); time.sleep(0.25)  # 赤
        dev.acop("01000000"); time.sleep(0.25)  # 黄


def warning_pulse(dev, seconds=5):
    """全色同時点滅で警告"""
    dev.acop("22200000", t=seconds)
    time.sleep(seconds + 0.2)


def countdown(dev, total=10):
    """カウントダウン: 長い間は緑、短くなると黄→赤点滅"""
    for i in range(total, 0, -1):
        if i > total * 2/3:
            dev.acop("00100000")   # 緑
        elif i > total / 3:
            dev.acop("01000000")   # 黄
        elif i > 0:
            dev.acop("20000000")   # 赤Blink
        print(f"  残り {i}秒")
        time.sleep(1)
    dev.all_off()
    print("  0! 終了")


# -------------------- CLI --------------------
PATTERNS = {
    "signal":    lambda d: signal_cycle(d, 3),
    "sos":       lambda d: morse(d, "SOS"),
    "rainbow":   lambda d: rainbow_chase(d, 15),
    "police":    lambda d: police(d, 15),
    "warning":   lambda d: warning_pulse(d, 3),
    "countdown": lambda d: countdown(d, 10),
}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("pattern", choices=list(PATTERNS) + ["all"])
    ap.add_argument("--host", default="192.168.1.150")
    args = ap.parse_args()

    dev = DN1000S(args.host)
    try:
        if args.pattern == "all":
            for name, fn in PATTERNS.items():
                print(f"=== {name} ===")
                fn(dev)
                dev.all_off()
                time.sleep(0.5)
        else:
            PATTERNS[args.pattern](dev)
    finally:
        dev.all_off()
