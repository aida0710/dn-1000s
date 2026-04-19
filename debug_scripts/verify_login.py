# -*- coding: utf-8 -*-
"""正しい認証と間違った認証の応答を比較して確実に検証"""
import http.client, socket, urllib.parse

HOST="192.168.1.150"

def post(path, body):
    conn = http.client.HTTPConnection(HOST, 80, timeout=5)
    conn.request("POST", path, body, {
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
    conn.close()
    return data

def get(path):
    conn = http.client.HTTPConnection(HOST, 80, timeout=5)
    conn.request("GET", path)
    s = conn.sock; s.settimeout(3)
    data=b""
    try:
        while True:
            c = s.recv(4096)
            if not c: break
            data += c
            if len(data) > 65536: break
    except socket.timeout: pass
    conn.close()
    return data

def try_creds(u,p, label):
    body = urllib.parse.urlencode({"user":u,"password":p,"login":"1","stat":"0"})
    r = post("/cgi-bin/login.cgi", body)
    text = r.decode("shift_jis","replace")
    print(f"\n{'='*50}")
    print(f"  {label}: user={u} pass={p}  ({len(r)} bytes)")
    print(f"{'='*50}")
    # 長い場合は中身の特徴的な部分だけ表示
    for kw in ["ログイン","menu","メニュー","パスワード","エラー","error","user","stat=","logout","monitor","不正","正しい","change"]:
        if kw in text:
            idx = text.find(kw)
            print(f"  '{kw}' @{idx}: ...{text[max(0,idx-30):idx+60]}...")

try_creds("admin","admin", "試行A (admin/admin)")
try_creds("admin","wrong_password_clearly", "試行B (admin/誤)")
try_creds("xxx","yyy", "試行C (無効ユーザ)")
try_creds("","", "試行D (空)")
