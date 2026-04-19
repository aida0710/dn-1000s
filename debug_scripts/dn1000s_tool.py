# -*- coding: utf-8 -*-
"""
DN-1000S パトランプ 汎用シリアル通信ツール
- プロトコル不明時の調査用
- PySerial 必須: pip install pyserial
"""
import serial
import serial.tools.list_ports
import time
import sys
import itertools

# ====== 設定 ======
PORT = "COM3"           # 環境に合わせて変更
BAUD_CANDIDATES = [9600, 19200, 38400, 57600, 115200, 4800, 2400]
TIMEOUT = 0.5
# ==================


def list_ports():
    print("=== 利用可能な COM ポート ===")
    for p in serial.tools.list_ports.comports():
        print(f"  {p.device}  {p.description}")
    print()


def open_port(port, baud):
    return serial.Serial(
        port=port,
        baudrate=baud,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=TIMEOUT,
    )


def send_raw(ser, data: bytes, wait=0.2):
    ser.reset_input_buffer()
    ser.write(data)
    ser.flush()
    time.sleep(wait)
    return ser.read_all()


def probe_baudrates(port):
    """ボーレートを総当たりで試し、何らかの応答があるか確認"""
    probes = [b"\r\n", b"?\r\n", b"AT\r\n", b"STATUS\r\n", b"HELP\r\n", b"\x05", b"\x1b"]
    for baud in BAUD_CANDIDATES:
        try:
            with open_port(port, baud) as ser:
                print(f"[baud={baud}] 試行中...")
                for p in probes:
                    resp = send_raw(ser, p)
                    if resp:
                        print(f"  -> 送信:{p!r}  応答:{resp!r}")
        except Exception as e:
            print(f"  baud={baud} エラー: {e}")


def interactive(port, baud):
    """対話モード: 手打ちでコマンド送信"""
    print(f"[対話モード] {port} @ {baud}")
    print("  'hex:' で始めると16進入力(例: hex:0205AA01). 'quit' で終了.")
    with open_port(port, baud) as ser:
        while True:
            line = input("> ").strip()
            if line in ("quit", "exit"):
                break
            if line.startswith("hex:"):
                try:
                    data = bytes.fromhex(line[4:].replace(" ", ""))
                except ValueError as e:
                    print(f"  16進パース失敗: {e}")
                    continue
            else:
                data = (line + "\r\n").encode()
            resp = send_raw(ser, data, wait=0.3)
            print(f"  応答(hex): {resp.hex(' ')}")
            print(f"  応答(txt): {resp!r}")


def brute_force_password(port, baud, cmd_template, pw_format="{:04d}", start=0, end=10000):
    """
    数字パスワード総当たり(自機向けのみ・自己責任で実行).
    cmd_template: 例 "UNLOCK {pw}\r\n"  -- {pw} がパスワードに置換される
    pw_format: "{:04d}" なら 0000-9999
    """
    print(f"[ブルートフォース] baud={baud} range={start}-{end}")
    with open_port(port, baud) as ser:
        for i in range(start, end):
            pw = pw_format.format(i)
            cmd = cmd_template.replace("{pw}", pw).encode()
            resp = send_raw(ser, cmd, wait=0.05)
            if resp and b"OK" in resp.upper():
                print(f"  *** ヒット! pw={pw}  応答={resp!r}")
                return pw
            if i % 100 == 0:
                print(f"  {pw} ... resp={resp!r}")
    return None


# ---- パトランプの典型的な制御例 (プロトコル判明後に書き換える) ----
def example_patlamp_control(port, baud):
    """一般的なシリアルパトランプ風: 1バイトの色指定を送る"""
    COLORS = {
        "off":   b"\x00",
        "red":   b"\x01",
        "green": b"\x02",
        "amber": b"\x04",
        "buzzer":b"\x08",
    }
    with open_port(port, baud) as ser:
        for name, code in COLORS.items():
            print(f"送信: {name} -> {code.hex()}")
            send_raw(ser, code, wait=0.8)
        send_raw(ser, COLORS["off"])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("使い方:")
        print("  python dn1000s_tool.py list")
        print("  python dn1000s_tool.py probe [COM3]")
        print("  python dn1000s_tool.py shell COM3 9600")
        print("  python dn1000s_tool.py demo  COM3 9600")
        sys.exit(0)

    mode = sys.argv[1]
    if mode == "list":
        list_ports()
    elif mode == "probe":
        port = sys.argv[2] if len(sys.argv) > 2 else PORT
        probe_baudrates(port)
    elif mode == "shell":
        interactive(sys.argv[2], int(sys.argv[3]))
    elif mode == "demo":
        example_patlamp_control(sys.argv[2], int(sys.argv[3]))
    else:
        print(f"不明なモード: {mode}")
