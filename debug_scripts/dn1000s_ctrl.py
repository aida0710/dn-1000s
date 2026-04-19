# -*- coding: utf-8 -*-
"""
DN-1000S (警子ちゃんミニ) 制御ライブラリ

rsh プロトコル (TCP 514) で直接コマンドを送信
 - Web UI への事前ログインは不要 (コマンドアクセス設定で登録されたユーザならOK)
 - パスワード検査は PWST 設定と -p オプション次第
"""
import socket
import struct

HOST = "192.168.1.150"
RSH_PORT = 514

def rsh(host, cmd, local_user="isa", remote_user="isa", port=RSH_PORT, timeout=5):
    """
    RFC1282 rsh プロトコルを Python で実装 (シンプル版)
    注意: UNIX rsh は特権ポート(<1024)からの接続を要求するが、ここでは無視
          (機器側が特権チェックしていないことを期待)
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((host, port))
    # stderr用ポート番号 (0 = 使わない) を ASCII で送る
    payload = b"0\0"
    payload += local_user.encode() + b"\0"
    payload += remote_user.encode() + b"\0"
    payload += cmd.encode() + b"\0"
    s.sendall(payload)
    # 応答: 最初の1バイトが NUL なら成功。その後のデータは stdout
    resp = b""
    try:
        while True:
            chunk = s.recv(4096)
            if not chunk: break
            resp += chunk
            if len(resp) > 8192: break
    except socket.timeout:
        pass
    s.close()
    return resp


# ---- 高レベル関数 ----

def help_cmd(password=None):
    cmd = "HELP"
    if password: cmd += f" -p {password}"
    return rsh(HOST, cmd)

def version(password=None):
    cmd = "VERN"
    if password: cmd += f" -p {password}"
    return rsh(HOST, cmd)

def lamp(n, action="TurnOn", password=None, w=None, t=None):
    """n: 1=赤, 2=黄, 3=緑, 4=ブザー等; action: TurnOn/TurnOff/Blink"""
    cmd = f"RLY{n} {action}"
    if w is not None: cmd += f" -w {w}"
    if t is not None: cmd += f" -t {t}"
    if password: cmd += f" -p {password}"
    return rsh(HOST, cmd)

def alarm_off(password=None):
    cmd = "ALOF"
    if password: cmd += f" -p {password}"
    return rsh(HOST, cmd)

def acop(pattern, password=None):
    """8桁文字列 (x=変更なし, 0/1/2=各状態) でランプ/ブザー一括制御"""
    cmd = f"ACOP {pattern}"
    if password: cmd += f" -p {password}"
    return rsh(HOST, cmd)


if __name__ == "__main__":
    import sys
    print(f"[*] DN-1000S @ {HOST} rshテスト")
    print()
    # まず特権ポートなしで接続テスト
    try:
        print("=== HELP ===")
        r = help_cmd()
        print(r.decode("shift_jis","replace"))
    except Exception as e:
        print(f"接続エラー: {e}")
        print(" -> rsh サーバがTCP/514で動いていない可能性")
        print(" -> または特権ポート制約。ポートスキャンで確認します")
        # 代替: 関連ポートをスキャン
        for port in [514, 512, 513, 515, 2001, 4000, 5000, 23, 79]:
            s = socket.socket()
            s.settimeout(1.0)
            try:
                s.connect((HOST, port))
                print(f"  TCP {port}: OPEN")
                s.close()
            except Exception:
                pass
        sys.exit(1)

    print("\n=== VERN ===")
    print(version().decode("shift_jis","replace"))

    print("\n=== 赤ランプを3秒点灯して自動消灯 (RLY1 TurnOn -t 3) ===")
    r = lamp(1, "TurnOn", t=3)
    print(r.decode("shift_jis","replace"))
