# -*- coding: utf-8 -*-
"""
NTP診断: 機器から発信されるタイムプロトコルパケットを観測
 1) unit.cgi の time_addr を PC IP (192.168.1.14) に書き換え
 2) UDP123 / UDP37 / TCP37 を同時listen
 3) 機器を reboot してパケット観察
"""
import http.client, socket, urllib.parse, re, threading, time, select, sys

DN1000 = "192.168.1.150"
MY_IP  = "192.168.1.14"    # 機器の time_addr に書き込む値

def get_cookie_login():
    conn = http.client.HTTPConnection(DN1000, 80, timeout=5)
    body = urllib.parse.urlencode({"user":"DN1000","password":"DN1000","login":"1","stat":"0"})
    conn.request("POST","/cgi-bin/login.cgi",body,
                 {"Content-Type":"application/x-www-form-urlencoded",
                  "Content-Length":str(len(body))})
    s=conn.sock; s.settimeout(3)
    while True:
        try:
            c=s.recv(4096)
            if not c: break
        except: break
    conn.close()

def fetch(path):
    conn = http.client.HTTPConnection(DN1000, 80, timeout=5)
    conn.request("GET", path)
    s=conn.sock; s.settimeout(3); d=b""
    while True:
        try:
            c=s.recv(4096)
            if not c: break
            d+=c
        except: break
    conn.close()
    if d.startswith(b"HTTP/"): d = d[d.find(b"\r\n\r\n")+4:]
    return d.decode("shift_jis","replace")

def post(path, fields):
    body = urllib.parse.urlencode(fields).encode("shift_jis")
    conn = http.client.HTTPConnection(DN1000, 80, timeout=5)
    conn.request("POST", path, body,
                 {"Content-Type":"application/x-www-form-urlencoded",
                  "Content-Length":str(len(body))})
    s=conn.sock; s.settimeout(3); d=b""
    while True:
        try:
            c=s.recv(4096)
            if not c: break
            d+=c
        except: break
    conn.close()
    if d.startswith(b"HTTP/"): d = d[d.find(b"\r\n\r\n")+4:]
    return d.decode("shift_jis","replace")

def extract_all_fields(html):
    """既存値を全部取得 (INPUT + SELECT radioも)"""
    fields = {}
    # <INPUT ... NAME=xxx value=yyy>
    for m in re.finditer(r"<INPUT[^>]*NAME=['\"]?([\w_]+)['\"]?[^>]*>", html, re.I):
        tag = m.group(0)
        name = m.group(1)
        # value 抽出
        vm = re.search(r"value=['\"]?([^'\"> ]*)['\"]?", tag, re.I)
        # radio は checked のみ有効
        if "type=" in tag.lower():
            tm = re.search(r"type=['\"]?(\w+)", tag, re.I)
            typ = tm.group(1).lower() if tm else ""
            if typ == "radio":
                if "checked" in tag.lower():
                    fields[name] = vm.group(1) if vm else ""
                continue
            if typ == "checkbox":
                if "checked" in tag.lower():
                    fields[name] = vm.group(1) if vm else "on"
                continue
            if typ in ("button","reset","submit"):
                continue
        fields[name] = vm.group(1) if vm else ""
    # SELECT の選択値
    for m in re.finditer(r"<SELECT[^>]*NAME=['\"]?([\w_]+)['\"]?[^>]*>(.+?)</SELECT>", html, re.S|re.I):
        name = m.group(1); inner = m.group(2)
        om = re.search(r"<OPTION[^>]*SELECTED[^>]*value=['\"]?([^'\"> ]+)", inner, re.I) \
             or re.search(r"value=['\"]?([^'\"> ]+)[^>]*SELECTED", inner, re.I)
        if om: fields[name] = om.group(1)
    return fields

def main():
    print("[1/4] ログイン")
    get_cookie_login()

    print("[2/4] unit.cgi の既存フィールド取得")
    html = fetch("/cgi-bin/unit.cgi?stat=1")
    fields = extract_all_fields(html)
    print(f"    抽出フィールド数: {len(fields)}")

    # time_addr を PC IP に差し替え
    pc_octets = MY_IP.split(".")
    for i,v in enumerate(pc_octets,1):
        fields[f"time_addr{i}"] = v
    # 保存フラグ
    fields["set"] = "1"
    fields["stat"] = "1"

    print(f"[3/4] time_addr を {MY_IP} に書き込み POST")
    resp = post("/cgi-bin/unit.cgi", fields)
    ok = "エラー" not in resp and "error" not in resp.lower()
    print(f"    結果: {'OK' if ok else 'NG'}")

    # 書き込み確認
    html = fetch("/cgi-bin/unit.cgi?stat=1")
    m = [re.search(rf"NAME=['\"]?time_addr{n}['\"]?[^>]*value=['\"]?(\d+)", html).group(1) for n in range(1,5)]
    print(f"    読み戻し: time_addr = {'.'.join(m)}")

    print("[4/4] UDP123/UDP37/TCP37 を 60秒 listen")
    print("     → この間に Web UIで機器を再起動してください")

    # 3ポート同時listen
    socks = []
    for port,proto in [(123,"UDP-NTP"),(37,"UDP-TIME")]:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
            socks.append((s, port, proto))
            print(f"  listen {proto} ({port}/udp) OK")
        except OSError as e:
            print(f"  listen {proto} ({port}/udp) FAIL: {e}")
    ts = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ts.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        ts.bind(("0.0.0.0", 37)); ts.listen(4)
        ts.setblocking(False)
        print(f"  listen TCP-TIME (37/tcp) OK")
    except OSError as e:
        ts = None; print(f"  listen TCP-TIME FAIL: {e}")

    t_end = time.time() + 60
    seen = False
    while time.time() < t_end:
        readers = [s for s,_,_ in socks]
        if ts: readers.append(ts)
        r,_,_ = select.select(readers, [], [], 1.0)
        for s in r:
            if ts and s is ts:
                try:
                    conn,addr = s.accept()
                    print(f"  [{time.strftime('%H:%M:%S')}] *** TCP37 接続 from {addr} ***")
                    seen = True
                    data = conn.recv(64)
                    print(f"    payload: {data!r}")
                    conn.close()
                except BlockingIOError:
                    pass
            else:
                data,addr = s.recvfrom(1024)
                for sock,port,proto in socks:
                    if sock is s:
                        print(f"  [{time.strftime('%H:%M:%S')}] *** {proto} ({port}/udp) パケット from {addr}: {len(data)}B ***")
                        print(f"    dump: {data.hex()}")
                        seen = True
                        break

    print("[done]", "パケット観測成功" if seen else "60秒間パケット無し")

if __name__ == "__main__":
    main()
