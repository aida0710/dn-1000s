# -*- coding: utf-8 -*-
"""自動再起動+listen。time_addr設定済み前提"""
import http.client, urllib.parse, socket, select, time, threading, re

DN="192.168.1.150"

def login():
    conn = http.client.HTTPConnection(DN,80,timeout=5)
    b = urllib.parse.urlencode({"user":"DN1000","password":"DN1000","login":"1","stat":"0"})
    conn.request("POST","/cgi-bin/login.cgi",b,
                 {"Content-Type":"application/x-www-form-urlencoded","Content-Length":str(len(b))})
    s=conn.sock; s.settimeout(3)
    while True:
        try:
            c=s.recv(4096)
            if not c: break
        except: break
    conn.close()

def get_time():
    conn = http.client.HTTPConnection(DN,80,timeout=5)
    conn.request("GET","/cgi-bin/monitor.cgi?stat=1")
    s=conn.sock; s.settimeout(3); d=b""
    while True:
        try:
            c=s.recv(4096)
            if not c: break
            d+=c
        except: break
    conn.close()
    if d.startswith(b"HTTP/"): d = d[d.find(b"\r\n\r\n")+4:]
    text=d.decode("shift_jis","replace")
    m = re.search(r"現在時刻[：: ]+([^<\n]+)", text)
    return m.group(1).strip() if m else None

def check_time_addr():
    conn = http.client.HTTPConnection(DN,80,timeout=5)
    conn.request("GET","/cgi-bin/unit.cgi?stat=1")
    s=conn.sock; s.settimeout(3); d=b""
    while True:
        try:
            c=s.recv(4096)
            if not c: break
            d+=c
        except: break
    conn.close()
    if d.startswith(b"HTTP/"): d = d[d.find(b"\r\n\r\n")+4:]
    html=d.decode("shift_jis","replace")
    octs=[]
    for n in range(1,5):
        m=re.search(rf"NAME=['\"]?time_addr{n}['\"]?[^>]*value=['\"]?(\d+)", html)
        octs.append(m.group(1) if m else "?")
    return ".".join(octs)

def reboot():
    """reboot.cgi を叩く"""
    try:
        conn=http.client.HTTPConnection(DN,80,timeout=3)
        conn.request("GET","/cgi-bin/reboot.cgi?stat=1&confirm=1&set=1")
        s=conn.sock; s.settimeout(2); d=b""
        try:
            while True:
                c=s.recv(4096)
                if not c: break
                d+=c
        except: pass
        conn.close()
        return d.decode("shift_jis","replace")[:200]
    except Exception as e:
        return f"err: {e}"

login()
print(f"[*] 現在時刻 (機器): {get_time()}")
print(f"[*] time_addr 設定: {check_time_addr()}")

# listen開始 (別スレッド)
socks=[]
for p in (123,37):
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0",p)); socks.append((s,p))
ts=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ts.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
ts.bind(("0.0.0.0",37)); ts.listen(4); ts.setblocking(False)
print(f"[*] listening UDP123/UDP37/TCP37")

seen=[]
lock=threading.Lock()
stop=threading.Event()
def listener():
    while not stop.is_set():
        rd=[s for s,_ in socks]+[ts]
        r,_,_=select.select(rd,[],[],0.5)
        for s in r:
            if s is ts:
                try:
                    conn,addr=s.accept()
                    with lock: seen.append(("tcp37",addr,b""))
                    print(f"  [{time.strftime('%H:%M:%S')}] TCP37 from {addr}")
                    conn.close()
                except: pass
            else:
                try:
                    data,addr=s.recvfrom(1024)
                    for sk,p in socks:
                        if sk is s:
                            with lock: seen.append((f"udp{p}",addr,data))
                            print(f"  [{time.strftime('%H:%M:%S')}] UDP{p} from {addr}: {len(data)}B hex={data[:16].hex()}")
                            break
                except: pass
t=threading.Thread(target=listener, daemon=True); t.start()

print(f"\n[*] reboot.cgi 叩く...")
print(f"    応答: {reboot()}")
print(f"[*] 機器復帰を 180秒待機+観察")

t_end = time.time()+180
last_status = 0
while time.time()<t_end:
    time.sleep(5)
    elapsed = int(time.time()-(t_end-180))
    print(f"  [{elapsed}s] seen={len(seen)}")

stop.set()
print(f"\n=== 結果 ===")
print(f"観測パケット: {len(seen)}")
try:
    print(f"機器の現在時刻: {get_time()}")
    print(f"time_addr確認: {check_time_addr()}")
except Exception as e:
    print(f"機器応答不可: {e}")
