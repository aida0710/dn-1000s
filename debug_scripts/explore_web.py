# -*- coding: utf-8 -*-
"""Webの全CGIを走査して音/ブザー関連のフォームを探す"""
import http.client, socket, urllib.parse, re

HOST="192.168.1.150"

def req(method, path, body=None):
    conn = http.client.HTTPConnection(HOST, 80, timeout=5)
    headers = {"Content-Type":"application/x-www-form-urlencoded"}
    if body:
        headers["Content-Length"] = str(len(body))
    conn.request(method, path, body, headers)
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
    # HTTP/0.9 は生ボディ。HTTP/1.x ならヘッダ付き
    if data.startswith(b"HTTP/"):
        i = data.find(b"\r\n\r\n")
        return data[i+4:] if i>0 else data
    return data

# ログイン
print("[*] ログイン...")
body = urllib.parse.urlencode({"user":"DN1000","password":"DN1000","login":"1","stat":"0"})
req("POST", "/cgi-bin/login.cgi", body)

CGIS = ["unit", "mon_setting", "mon_setting2", "mon_setting3",
        "opt_setting", "opt_setting3", "opt_setting4", "opt_setting5",
        "messager", "mail", "snmp", "rsh_user", "user", "time",
        "monitor", "eventlog0", "datalog0"]

for cgi in CGIS:
    r = req("GET", f"/cgi-bin/{cgi}.cgi?stat=1")
    text = r.decode("shift_jis","replace")
    print(f"\n=========== {cgi}.cgi ({len(r)}B) ===========")
    # 音/ブザー/音量関連のキーワードが含まれる行を抽出
    hits = []
    for kw in ["音","ブザー","音量","スピーカ","音声","VOL","volume","buzzer","speaker","SPOP","sound","BEEP","beep"]:
        for line in text.split("\n"):
            if kw in line and len(line.strip()) < 300:
                hits.append(line.strip())
    # 重複除去
    for h in sorted(set(hits))[:15]:
        print(f"  - {h}")
    # フォーム入力フィールドも抽出
    inputs = re.findall(r"<INPUT[^>]*>", text, re.I)
    if inputs:
        print(f"  [inputs: {len(inputs)}]")
        for i in inputs[:5]:
            print(f"    {i}")
