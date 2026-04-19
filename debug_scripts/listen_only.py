# -*- coding: utf-8 -*-
"""NTP/TIMEパケットのみ180秒listen (時刻設定は既に済み)"""
import socket, select, time

socks = []
for port in (123, 37):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("0.0.0.0", port)); socks.append((s,port,"udp"))
        print(f"  listen {port}/udp OK")
    except OSError as e:
        print(f"  listen {port}/udp NG: {e}")

ts = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ts.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
ts.bind(("0.0.0.0", 37)); ts.listen(4); ts.setblocking(False)
print(f"  listen 37/tcp OK")

print("\n★ 今すぐWeb UIで機器を再起動してください (180秒タイマー)")

t_end = time.time() + 180
seen = 0
while time.time() < t_end:
    readers = [s for s,_,_ in socks] + [ts]
    r,_,_ = select.select(readers, [], [], 1.0)
    for s in r:
        if s is ts:
            try:
                conn,addr = s.accept()
                print(f"[{time.strftime('%H:%M:%S')}] *** TCP37 from {addr} ***")
                seen += 1
                try: data=conn.recv(64); print(f"  data={data!r}")
                except: pass
                conn.close()
            except BlockingIOError: pass
        else:
            try:
                data,addr = s.recvfrom(1024)
                for sock,port,_ in socks:
                    if sock is s:
                        print(f"[{time.strftime('%H:%M:%S')}] *** UDP{port} from {addr}  {len(data)}B ***")
                        print(f"  hex: {data[:64].hex()}")
                        seen += 1
                        break
            except: pass
    if int(time.time()) % 10 == 0 and int(time.time()) != int(t_end):
        print(f"  ... {int(t_end-time.time())}秒残")
        time.sleep(1)

print(f"\n結果: {seen}パケット観測")
