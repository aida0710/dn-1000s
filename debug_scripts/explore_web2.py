# -*- coding: utf-8 -*-
"""unit.cgi 全体と 196B の正体確認"""
import http.client, socket, urllib.parse, re

HOST="192.168.1.150"

def req(method, path, body=None):
    conn = http.client.HTTPConnection(HOST, 80, timeout=5)
    h = {"Content-Type":"application/x-www-form-urlencoded"}
    if body: h["Content-Length"] = str(len(body))
    conn.request(method, path, body, h)
    s = conn.sock; s.settimeout(3)
    data=b""
    try:
        while True:
            c = s.recv(4096)
            if not c: break
            data += c
            if len(data) > 131072: break
    except socket.timeout: pass
    conn.close()
    if data.startswith(b"HTTP/"):
        i = data.find(b"\r\n\r\n")
        return data[i+4:] if i>0 else data
    return data

# ログイン
body = urllib.parse.urlencode({"user":"DN1000","password":"DN1000","login":"1","stat":"0"})
req("POST","/cgi-bin/login.cgi", body)

# 196Bの正体
print("=== mon_setting.cgi 生 ===")
r = req("GET","/cgi-bin/mon_setting.cgi?stat=1")
print(r.decode("shift_jis","replace"))

print("\n=== unit.cgi 全INPUTフィールド ===")
r = req("GET","/cgi-bin/unit.cgi?stat=1")
text = r.decode("shift_jis","replace")
# INPUT全部抽出
for m in re.finditer(r"<(?:INPUT|SELECT|TEXTAREA)[^>]*>", text, re.I):
    print(f"  {m.group(0)}")

# unit.cgi 内の見出し/ラベルを抽出
print("\n=== unit.cgi の表示テキスト ===")
# タグ除去
plain = re.sub(r"<[^>]+>", " ", text)
plain = re.sub(r"\s+", " ", plain)
# 音/ブザー/音量が含まれる部分を抜き出す
for kw in ["音量","音声","ブザー","スピーカ","鳴動","Buzzer"]:
    idx = 0
    while True:
        i = plain.find(kw, idx)
        if i < 0: break
        print(f"  ...{plain[max(0,i-40):i+80]}...")
        idx = i+1
