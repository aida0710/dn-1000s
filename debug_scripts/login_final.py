# -*- coding: utf-8 -*-
"""型番パターンの初期認証を試す"""
import http.client, socket, urllib.parse

HOST="192.168.1.150"

def post(body):
    conn = http.client.HTTPConnection(HOST, 80, timeout=5)
    conn.request("POST", "/cgi-bin/login.cgi", body, {
        "Content-Type":"application/x-www-form-urlencoded",
        "Content-Length": str(len(body)),
    })
    s = conn.sock; s.settimeout(3)
    data=b""
    try:
        while True:
            c = s.recv(4096)
            if not c: break
            data += c
            if len(data) > 32768: break
    except socket.timeout: pass
    # Cookie ヘッダも取得するため
    conn.close()
    return data

def try_creds(u,p):
    body = urllib.parse.urlencode({"user":u,"password":p,"login":"1","stat":"0"})
    r = post(body)
    t = r.decode("shift_jis","replace")
    fail = "間違っています" in t or "パスワードが" in t
    # 成功時はセッション発行や別画面への遷移があるはず
    return (not fail), t

CREDS = [
    ("DN1000","DN1000"),
    ("DN1000S","DN1000S"),
    ("dn1000","dn1000"),
    ("dn1000s","dn1000s"),
    ("DN1000s","DN1000s"),
    ("DN-1000","DN-1000"),
    ("DN-1000S","DN-1000S"),  # これは8文字超過だけど一応
    ("dn-1000","dn-1000"),
]

for u,p in CREDS:
    ok, snippet = try_creds(u, p)
    print(f"{u:10s} / {p:10s} -> {'*** HIT ***' if ok else 'fail'}")
    if ok:
        # 認証成功の中身を見る
        idx = snippet.find("本体情報") if "本体情報" in snippet else 0
        print(f"  応答の冒頭200文字:")
        print(f"  {snippet[idx:idx+500]}")
        break
