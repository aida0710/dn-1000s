# -*- coding: utf-8 -*-
"""
Webhook受信サーバ — DN-1000S をアラート通知灯として使う

標準ライブラリのみ。外部依存なし。

--- 対応フォーマット ---
POST /alert                         (独自JSON)
POST /grafana                       (Grafana Alertmanager webhook)
POST /github                        (GitHub webhook)
POST /                              (プレーン: クエリ文字列 or JSON)

--- 独自JSON形式 ---
  { "severity": "critical|warning|ok", "message": "..." }
  { "color": "red|yellow|green", "mode": "on|off|blink", "seconds": 30 }

--- クエリ文字列形式 (プレーン) ---
  curl -X POST "http://localhost:8080/?color=red&mode=blink&seconds=10"

使い方:
    python webhook_server.py                      # port 8080 デフォルト
    python webhook_server.py --port 9000
    python webhook_server.py --host 192.168.1.150 --bind 0.0.0.0 --port 8080

テスト:
    curl -X POST http://localhost:8080/alert \\
         -H "Content-Type: application/json" \\
         -d '{"severity":"critical","message":"DB down"}'

    curl -X POST "http://localhost:8080/?color=green&mode=on&seconds=5"
"""
import argparse
import json
import os
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from debug_scripts.dn1000s import DN1000S


# -------- アラート実行 --------
_lock = threading.Lock()
_timer: threading.Timer | None = None


def apply(dev: DN1000S, color: str, mode: str, seconds: int | None = None):
    """ランプ制御を排他で行う。秒指定があれば自動で全OFFする"""
    global _timer
    with _lock:
        # 既存タイマーをキャンセル
        if _timer:
            _timer.cancel()
            _timer = None
        ch = {"red": dev.red, "yellow": dev.yellow, "green": dev.green,
              "buzzer_cont": dev.buzzer_cont, "buzzer_disc": dev.buzzer_disc}.get(color)
        if ch is None:
            return f"unknown color: {color}"
        if mode == "on":
            ch.on()
        elif mode == "off":
            ch.off()
        elif mode == "blink":
            ch.blink()
        else:
            return f"unknown mode: {mode}"

        if seconds:
            _timer = threading.Timer(seconds, lambda: dev.all_off())
            _timer.daemon = True
            _timer.start()
        return f"ok: {color} {mode} {seconds or ''}"


# -------- severity → 色/モード --------
SEVERITY_MAP = {
    # アラート系
    "critical":  ("red",    "blink", 60),
    "fatal":     ("red",    "blink", 60),
    "error":     ("red",    "on",    60),
    "alert":     ("red",    "blink", 60),
    "warning":   ("yellow", "on",    60),
    "warn":      ("yellow", "on",    60),
    "notice":    ("yellow", "on",    30),
    "info":      ("green",  "on",    10),
    # 回復系
    "ok":        ("green",  "on",    5),
    "resolved":  ("green",  "on",    5),
    "recovered": ("green",  "on",    5),
}


# -------- ハンドラ --------
class Handler(BaseHTTPRequestHandler):
    dev: DN1000S = None   # will be assigned

    def log_message(self, fmt, *a):
        print(f"[{time.strftime('%H:%M:%S')}] {self.address_string()} - {fmt%a}")

    def do_GET(self):
        if self.path == "/":
            self._json(200, {"status": "ready", "endpoints":
                             ["/alert", "/grafana", "/github", "/"]})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        # body
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""

        path = urllib.parse.urlparse(self.path).path
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))

        try:
            if path == "/alert":
                result = self._handle_alert(body)
            elif path == "/grafana":
                result = self._handle_grafana(body)
            elif path == "/github":
                result = self._handle_github(body, self.headers.get("X-GitHub-Event", ""))
            else:
                # プレーンなクエリ文字列 or JSON
                result = self._handle_plain(body, query)
            self._json(200, {"result": result})
        except Exception as e:
            self._json(500, {"error": str(e)})

    # --- ルート別処理 ---
    def _handle_alert(self, body):
        """独自JSON: {"severity": "critical", "message": "..."}
                     {"color":"red", "mode":"blink", "seconds":30}"""
        d = json.loads(body)
        if "severity" in d:
            color, mode, sec = SEVERITY_MAP.get(
                d["severity"].lower(), ("yellow", "on", 30))
            print(f"  severity={d['severity']} msg={d.get('message','')!r}")
            return apply(self.dev, color, mode, sec)
        return apply(self.dev,
                     d.get("color", "yellow"),
                     d.get("mode", "on"),
                     d.get("seconds"))

    def _handle_grafana(self, body):
        """Grafana Alertmanager / Unified Alerting webhook"""
        d = json.loads(body)
        status = d.get("status", "firing")
        alerts = d.get("alerts", [])
        # firing の中で最も重い severity を採用
        worst = "info"
        order = ["info", "notice", "warning", "error", "critical"]
        for a in alerts:
            if a.get("status", "firing") == "firing":
                sev = a.get("labels", {}).get("severity", "warning").lower()
                if order.index(sev) > order.index(worst):
                    worst = sev
        if status == "resolved":
            worst = "resolved"
        color, mode, sec = SEVERITY_MAP.get(worst, ("yellow", "on", 30))
        print(f"  grafana: status={status} worst={worst} alerts={len(alerts)}")
        return apply(self.dev, color, mode, sec)

    def _handle_github(self, body, event):
        """GitHub webhook (push/pull_request/workflow_run など)"""
        d = json.loads(body)
        if event == "workflow_run":
            conclusion = d.get("workflow_run", {}).get("conclusion")
            if conclusion == "success":
                return apply(self.dev, "green", "on", 5)
            elif conclusion == "failure":
                return apply(self.dev, "red", "blink", 60)
            else:
                return apply(self.dev, "yellow", "on", 10)
        elif event == "push":
            return apply(self.dev, "green", "blink", 3)
        elif event == "pull_request":
            action = d.get("action")
            if action == "opened":
                return apply(self.dev, "yellow", "blink", 5)
            elif action == "closed" and d.get("pull_request", {}).get("merged"):
                return apply(self.dev, "green", "on", 5)
        return "ignored"

    def _handle_plain(self, body, query):
        """クエリ or JSON を柔軟に解釈"""
        if body:
            try:
                d = json.loads(body)
                return apply(self.dev,
                             d.get("color", "yellow"),
                             d.get("mode", "on"),
                             d.get("seconds"))
            except json.JSONDecodeError:
                pass
        color = query.get("color", "yellow")
        mode = query.get("mode", "on")
        sec = int(query["seconds"]) if "seconds" in query else None
        return apply(self.dev, color, mode, sec)

    # --- 返却ヘルパ ---
    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="192.168.1.150", help="DN-1000S の IP")
    ap.add_argument("--bind", default="0.0.0.0", help="サーバの listen アドレス")
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()

    Handler.dev = DN1000S(args.host)
    srv = ThreadingHTTPServer((args.bind, args.port), Handler)
    print(f"[*] webhook server listening on {args.bind}:{args.port}")
    print(f"    DN-1000S target: {args.host}")
    print("    endpoints: /alert  /grafana  /github  /")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[停止] 全OFF")
        Handler.dev.all_off()


if __name__ == "__main__":
    main()
