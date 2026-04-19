# -*- coding: utf-8 -*-
"""
起動時にBIOSプロンプトを捕獲する:
 - ポートを開いた瞬間から Ctrl-C, Enter, ESC を短間隔で連打
 - BIOS(0)> を検出したら止める
 - その後、対話モードに入り任意のコマンドを送れる
"""
import serial, time, sys, threading

PORT="COM3"; BAUD=9600

def drain_async(ser, buf_ref, stop_evt):
    while not stop_evt.is_set():
        d = ser.read_all()
        if d:
            buf_ref.append(d)
            sys.stdout.write(d.decode("ascii","replace"))
            sys.stdout.flush()
        time.sleep(0.03)

def main():
    print("[bios_trap] ポートを開きます。すぐに機器の電源を入れてください")
    with serial.Serial(PORT, BAUD, timeout=0.2) as ser:
        buf = []
        stop = threading.Event()
        t = threading.Thread(target=drain_async, args=(ser,buf,stop), daemon=True)
        t.start()

        # 起動〜BIOS区間で割り込みキーを連打
        t_end = time.time() + 15.0
        got_bios = False
        while time.time() < t_end and not got_bios:
            # Ctrl-C, Enter, ESC を順番に送る
            for key in [b"\x03", b"\r", b"\x1b", b" "]:
                ser.write(key)
                time.sleep(0.08)
                data = b"".join(buf)
                if b"BIOS(" in data and b">" in data.split(b"BIOS(")[-1]:
                    print("\n\n[*** BIOSプロンプトを捕獲 ***]")
                    got_bios = True
                    break
        if not got_bios:
            print("\n[!] BIOSを捕まえられませんでした")
            stop.set()
            return

        time.sleep(0.5)
        # 対話モード
        print("\n[対話モード — 空行で終了, hex: で16進送信可]")
        while True:
            try:
                line = input("BIOS> ").strip()
            except EOFError:
                break
            if not line:
                break
            if line.startswith("hex:"):
                data = bytes.fromhex(line[4:].replace(" ",""))
            else:
                data = line.encode()+b"\r"
            ser.write(data)
            time.sleep(1.0)
        stop.set()

if __name__=="__main__":
    main()
