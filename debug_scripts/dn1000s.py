# -*- coding: utf-8 -*-
"""
DN-1000S (ISA 警子ちゃんミニ) 制御ライブラリ

ファームウェア仕様:
  - 制御プロトコル: rsh (TCP 514), 特権ポート(<1024)からの接続が必要
  - 認証: rsh サーバ側の登録ユーザー (root 等)
  - リレー: RLY1=赤 RLY2=黄 RLY3=緑
  - ブザー: ACOP の4桁目=連続, 5桁目=断続

使用例:
    from dn1000s import DN1000S

    dev = DN1000S("192.168.1.150")

    dev.red.on(t=3)           # 赤ランプを3秒点灯
    dev.green.blink(w=1, t=5) # 緑ランプを1秒周期で5秒点滅
    dev.yellow.off()          # 黄ランプ消灯

    dev.buzzer_cont.on(t=2)   # 連続ブザー2秒
    dev.buzzer_disc.on(t=2)   # 断続ブザー2秒

    dev.all_off()             # 全停止

    # 複雑なパターンは acop で1コマンド
    dev.acop("12000000", t=5) # 赤ON+黄Blink, 他OFF, 5秒後自動OFF

    # 生コマンド
    print(dev.raw("VERN"))    # バージョン
    print(dev.raw("HELP"))    # コマンド一覧
"""
from __future__ import annotations
import socket
import itertools
import threading
from typing import Optional


class _Channel:
    """ACOPの特定桁を制御するチャネル抽象。ランプ(RLY)もブザーもこのAPIで統一"""
    def __init__(self, device: "DN1000S", position: int, label: str, has_rly: bool = True):
        self._dev = device
        self._pos = position          # 1..8 (ACOP 8桁中の位置)
        self._label = label
        self._has_rly = has_rly       # True なら RLY コマンドで直接制御可、False なら ACOP経由

    def on(self, t: Optional[float] = None) -> str:
        if self._has_rly:
            cmd = f"RLY{self._pos} TurnOn"
            if t is not None: cmd += f" -t {t}"
            return self._dev.raw(cmd)
        return self._dev._acop_set(self._pos, "1", t=t)

    def off(self) -> str:
        if self._has_rly:
            return self._dev.raw(f"RLY{self._pos} TurnOff")
        return self._dev._acop_set(self._pos, "0")

    def blink(self, w: Optional[float] = None, t: Optional[float] = None) -> str:
        if self._has_rly:
            cmd = f"RLY{self._pos} Blink"
            if w is not None: cmd += f" -w {w}"
            if t is not None: cmd += f" -t {t}"
            return self._dev.raw(cmd)
        return self._dev._acop_set(self._pos, "2", w=w, t=t)

    def status(self) -> str:
        if self._has_rly:
            return self._dev.raw(f"RLY{self._pos}")
        return "(acop-only)"

    def __repr__(self):
        return f"<Channel {self._label} pos={self._pos}>"


class DN1000S:
    """
    DN-1000S コントローラ。

    :param host: 機器の IPアドレス
    :param rsh_user: 機器側で認証される rsh ユーザー (通常 "root")
    :param local_user: こちら側で名乗る rsh ローカルユーザー名
    :param password: PWST が Enabled の場合の追加パスワード
    :param timeout: rsh 接続/受信タイムアウト秒
    """

    # 特権ポートを使い回す (Windows は非特権プロセスでも bind 可)
    _port_iter = itertools.cycle(range(600, 1024))
    _port_lock = threading.Lock()

    def __init__(
        self,
        host: str,
        rsh_user: str = "root",
        local_user: str = "root",
        password: Optional[str] = None,
        timeout: float = 5.0,
    ):
        self.host = host
        self.rsh_user = rsh_user
        self.local_user = local_user
        self.password = password
        self.timeout = timeout

        # 各チャネル (RLY はコマンドあり、ブザーは ACOP経由)
        self.red         = _Channel(self, 1, "red",         has_rly=True)
        self.yellow      = _Channel(self, 2, "yellow",      has_rly=True)
        self.green       = _Channel(self, 3, "green",       has_rly=True)
        self.buzzer_cont = _Channel(self, 4, "buzzer_cont", has_rly=False)
        self.buzzer_disc = _Channel(self, 5, "buzzer_disc", has_rly=False)

    # ------------------------------------------------------------------
    # 低レベル: rsh プロトコル
    # ------------------------------------------------------------------
    def raw(self, command: str) -> str:
        """任意のコマンドを rsh で送り、応答文字列を返す"""
        if self.password and "-p " not in command:
            command = f"{command} -p {self.password}"

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        # 特権ポートから bind してから接続
        with self._port_lock:
            for _ in range(80):
                try:
                    sock.bind(("0.0.0.0", next(self._port_iter)))
                    break
                except OSError:
                    continue
            else:
                raise RuntimeError("特権ポートを確保できません")

        try:
            sock.connect((self.host, 514))
            payload = (
                "0\0"
                + self.local_user + "\0"
                + self.rsh_user   + "\0"
                + command         + "\0"
            ).encode()
            sock.sendall(payload)
            resp = b""
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk: break
                    resp += chunk
                    if len(resp) > 65536: break
            except socket.timeout:
                pass
        finally:
            sock.close()

        # 最初の1バイトが NUL なら成功
        if resp.startswith(b"\x00"):
            return resp[1:].decode("shift_jis", "replace").rstrip()
        return resp.decode("shift_jis", "replace").rstrip()

    # ------------------------------------------------------------------
    # 中レベル: ACOP
    # ------------------------------------------------------------------
    def acop(
        self,
        pattern: str = "xxxxxxxx",
        w: Optional[float] = None,
        t: Optional[float] = None,
    ) -> str:
        """
        一括制御 (ランプ/ブザーを8桁で同時指定)

        pattern: 8文字。各桁が
            x = 現状維持
            0 = TurnOff
            1 = TurnOn
            2 = Blink
        位置:  1=赤 2=黄 3=緑 4=連続ブザー 5=断続ブザー 6-8=未使用
        """
        if len(pattern) != 8:
            raise ValueError("pattern must be 8 characters")
        cmd = f"ACOP {pattern}"
        if w is not None: cmd += f" -w {w}"
        if t is not None: cmd += f" -t {t}"
        return self.raw(cmd)

    def _acop_set(
        self,
        pos: int,
        value: str,
        w: Optional[float] = None,
        t: Optional[float] = None,
    ) -> str:
        """1桁だけ変更した ACOP を送る"""
        pat = list("xxxxxxxx")
        pat[pos - 1] = value
        return self.acop("".join(pat), w=w, t=t)

    # ------------------------------------------------------------------
    # 高レベル: 便利関数
    # ------------------------------------------------------------------
    def all_off(self) -> str:
        """ランプ・ブザーすべて停止"""
        return self.acop("00000000")

    def alarm_off(self) -> str:
        """ALOF: アラーム状態を解除 (一時的なテスト発報をキャンセル)"""
        return self.raw("ALOF")

    def version(self) -> str:
        return self.raw("VERN")

    def unit_id(self) -> str:
        return self.raw("UTID")

    def help(self) -> str:
        return self.raw("HELP")


# ==================================================================
# CLI
# ==================================================================
def _cli():
    import argparse, sys

    ap = argparse.ArgumentParser(description="DN-1000S 警子ちゃんミニ コントローラ")
    ap.add_argument("--host", default="192.168.1.150")
    ap.add_argument("--user", default="root")
    ap.add_argument("--password", default=None)

    sub = ap.add_subparsers(dest="cmd", required=True)

    # on/off/blink
    for name in ["on", "off", "blink"]:
        p = sub.add_parser(name, help=f"チャネルを{name}")
        p.add_argument("channel",
                       choices=["red", "yellow", "green",
                                "buzzer_cont", "buzzer_disc"],
                       help="対象チャネル")
        p.add_argument("-t", type=int, default=None, help="継続秒(自動OFF)")
        if name == "blink":
            p.add_argument("-w", type=int, default=None, help="点滅周期秒")

    # acop
    pa = sub.add_parser("acop", help="ACOP 一括制御 (8桁パターン)")
    pa.add_argument("pattern", help="xxxxxxxx形式 0=Off 1=On 2=Blink x=維持")
    pa.add_argument("-t", type=int, default=None)
    pa.add_argument("-w", type=int, default=None)

    # 情報系
    sub.add_parser("status", help="現在のランプ/ブザー状態")
    sub.add_parser("version", help="ファームウェアバージョン")
    sub.add_parser("help", help="機器のサポートコマンド一覧")
    sub.add_parser("alloff", help="全チャネルOFF")

    # 生コマンド
    pr = sub.add_parser("raw", help="任意の rsh コマンドを送信")
    pr.add_argument("command", nargs="+")

    args = ap.parse_args()
    dev = DN1000S(args.host, rsh_user=args.user, password=args.password)

    if args.cmd in ("on", "off", "blink"):
        ch = getattr(dev, args.channel)
        if args.cmd == "on":
            print(ch.on(t=args.t))
        elif args.cmd == "off":
            print(ch.off())
        else:
            print(ch.blink(w=args.w, t=args.t))

    elif args.cmd == "acop":
        print(dev.acop(args.pattern, w=args.w, t=args.t))

    elif args.cmd == "status":
        print(f"red:         {dev.red.status()}")
        print(f"yellow:      {dev.yellow.status()}")
        print(f"green:       {dev.green.status()}")
        print(f"buzzer_cont: {dev.buzzer_cont.status()}")
        print(f"buzzer_disc: {dev.buzzer_disc.status()}")

    elif args.cmd == "version":
        print(dev.version())

    elif args.cmd == "help":
        print(dev.help())

    elif args.cmd == "alloff":
        print(dev.all_off())

    elif args.cmd == "raw":
        print(dev.raw(" ".join(args.command)))


if __name__ == "__main__":
    _cli()
