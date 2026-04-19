# -*- coding: utf-8 -*-
"""
HTTPヘルスチェック → 結果で色分け
  2xx: 緑
  4xx: 黄
  5xx/接続エラー: 赤点滅

使い方:
    python http_healthcheck.py https://example.com/health
    python http_healthcheck.py https://example.com --interval 60
"""
import argparse, time, urllib.request, urllib.error, sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from debug_scripts.dn1000s import DN1000S


def check(url, timeout=5):
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        return r.getcode()
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--host", default="192.168.1.150")
    ap.add_argument("--interval", type=int, default=30)
    args = ap.parse_args()

    dev = DN1000S(args.host)
    last = None
    try:
        while True:
            code = check(args.url)
            state = ("green"  if 200 <= code < 400 else
                     "yellow" if 400 <= code < 500 else
                     "red")
            if state != last:
                last = state
                if state == "green":
                    dev.acop("00100000")     # 緑ON
                elif state == "yellow":
                    dev.acop("01000000")     # 黄ON
                else:
                    dev.acop("20000000")     # 赤Blink
                print(f"[{time.strftime('%H:%M:%S')}] {code} -> {state}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[停止]")
    finally:
        dev.all_off()


if __name__ == "__main__":
    main()
