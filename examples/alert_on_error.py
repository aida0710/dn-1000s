# -*- coding: utf-8 -*-
"""
サーバのエラー監視連動サンプル: ログファイルを tail して ERROR 検出で赤点滅

使い方:
    python alert_on_error.py /path/to/app.log
    python alert_on_error.py /path/to/app.log --pattern "CRITICAL|FATAL"
"""
import argparse, re, time, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from debug_scripts.dn1000s import DN1000S


def tail_f(path):
    """ログを tail -f 的に読む"""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if line:
                yield line.rstrip()
            else:
                time.sleep(0.2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logfile")
    ap.add_argument("--host", default="192.168.1.150")
    ap.add_argument("--pattern", default=r"\b(ERROR|CRITICAL|FATAL)\b")
    ap.add_argument("--alert-seconds", type=int, default=30,
                    help="アラート継続秒 (複数エラーで延長)")
    args = ap.parse_args()

    dev = DN1000S(args.host)
    pat = re.compile(args.pattern)

    print(f"[*] 監視開始: {args.logfile}  パターン={args.pattern}")
    dev.green.on()  # 正常状態で緑点灯

    last_alert_until = 0
    try:
        for line in tail_f(args.logfile):
            if pat.search(line):
                until = time.time() + args.alert_seconds
                if until > last_alert_until:
                    last_alert_until = until
                    dev.acop("20100000")  # 赤Blink, 緑Off
                print(f"[ALERT] {line}")
            # タイマー管理: アラート終了したら緑に戻す
            if last_alert_until and time.time() > last_alert_until:
                last_alert_until = 0
                dev.acop("00100000")     # 赤Off, 緑On
                print("[RECOVER] 緑に戻しました")
    except KeyboardInterrupt:
        print("\n[停止]")
    finally:
        dev.all_off()


if __name__ == "__main__":
    main()
