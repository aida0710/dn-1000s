# 生産中止したパトランプ「DN-1000S」のパスワードを忘れたので、シリアルコンソールから内部を解析して制御ライブラリを作るまで

## TL;DR

- 職場にあった古いネットワーク警告灯 **ISA 警子ちゃんミニ DN-1000S** (生産終了) の管理画面パスワードを忘れた
- 工場送付リセットは不可 (メーカーは当該製品のサポート終了)
- COMポート → シリアルコンソール → ブートローダ → EEPROM → Web UI の順に攻略し、制御用Pythonライブラリまで完成させた
- **工場出荷時パスワードは型番そのもの** (`DN1000 / DN1000`) と判明。型番別の後継機マニュアルから推測できた
- 途中で **EEPROM を誤消去** してMACアドレスも吹き飛ばしたが、ブートログから採取しておいた元のMACで完全復旧

一連の作業で使ったスクリプトはすべて記事末尾の GitHub リポジトリ相当に置いてあります。

---

## 1. 機器について

### DN-1000S「警子ちゃんミニ」

- メーカー: **株式会社アイエスエイ (ISA)**
- 製品: ネットワーク警告灯 (パトランプ)
- LAN 経由で HTTP / rsh / SNMP のコマンドを受けてランプ点灯・ブザー鳴動させる
- **2013年12月末に受注生産終了**。後継は DN-1500GX / DN-1700GX

| 項目 | 値 |
|---|---|
| CPU | Samsung S3C4XXX (ARM7TDMI) |
| OS | μClinux 2.2.14 + romfs |
| Flash | SST39VF160 × 2 (計 4MB) |
| RAM | 16MB |
| Ethernet | 10BASE-T (eth_s3c4 ドライバ) |
| ブートローダ | SBC8023 BIOS v00.022.0D (ISA独自) |

## 2. なぜ COM ポートに繋いだか

TCP/IP の LAN 経由で Web UI にアクセスしようとしたが、管理画面のパスワードを忘れている。

LAN 上では何も見えない (DHCP を取らない古いファームで、固定 IP が何に設定されているか分からない)。本体には RS-232C のポートがあったので、**USB-Serial 変換 (CH340)** でシリアルコンソールに接続することから始めた。

```
PC (Windows, Python 3.13, pyserial)
  └── USB-Serial CH340 (COM3, 9600 8N1)
       └── DN-1000S
```

## 3. シリアルから読めたブートログ (お宝)

9600bps で機器の電源を入れ直すと、ブートローダ → μClinux のカーネル → DN1000 アプリ までの全ログが流れてきた。

```
SBC8023 BIOS v00.022.0D (c) 2000-2005 ISA Co., Ltd.
...
eth_s3c4.c : v1.0.0 25/Apr/2000
eth0  00:a0:66:0f:59:52           ← 個体固有のMAC
...
SBC8023 mapped flash: Found 1 x 16Mb SST39VF160 compatible at 0x0
VFS: Mounted root (romfs filesystem).
----------------------------------------------------
DN1000 v03.077.4D (c) 2000-2008 ISA Co., Ltd.
----------------------------------------------------
```

**ここで後々の救世主となる MAC `00:a0:66:0f:59:52` を記録しておいたのがまさに命拾い** だった(詳細は§7)。

## 4. ログインプロンプトに騙される

ブート完了後に `login:` が出たので「Linuxコンソールログインだ」と思って、20 通りくらい定番の認証(`root/root`, `admin/admin`, `keiko/keiko` …) を総当たりしたが**全部失敗**。

詳しく観察すると、

- どのユーザ名を打っても `Password:` プロンプトが**出ない**
- 即座に `login:` に戻るだけ
- Ctrl-C / Ctrl-D / ESC など**制御文字もすべて無視**

本物の getty/login なら存在しないユーザでも Password: を出してくるはず。挙動的にこれは **μClinux の getty が `/bin/login` を呼び損ねてループしているダミープロンプト**と判断。シリアル経由ではユーザランドに入れない構造だった。

## 5. ブートローダ BIOS(0)> を捕まえる

電源投入直後に連打していると `BIOS(0)>` プロンプトが現れる。これは ISA 自製のブートローダ `SBC8023 BIOS`。さらに何かを連打すると、

```
Clear system parameters on IIC EEPROM....Done!

***  Configure the System parameters ***

IP Address [192.168.1.1]>
Gateway IP [192.168.1.254]>
Subnet Mask [255.255.255.0]>
TFTP Server IP [192.168.1.250]>
TFTP Boot File [c:\tftp\firm]>
Ethernet Address [00:A0:66:00:00:00] >
```

**工場出荷時ネットワーク設定が白日の下に!**

- 工場出荷 IP: `192.168.1.1`
- MAC プレフィックス: `00:A0:66:xx:xx:xx` (ISA の OUI)
- TFTP サーバ (`192.168.1.250:/c:\tftp\firm`) も用意されている = メーカーはファーム更新用 TFTP を想定

トリガーキーは検証の結果 **ESC (`\x1b`)** だった。Ctrl-C では入らない。

```python
# 電源 ON 直後から 100ms おきに ESC を送信
while not detected:
    ser.write(b"\x1b")
    time.sleep(0.1)
    if b"IP Address [" in buf:
        break
```

## 6. EEPROM を誤消去する事故

調査スクリプトが `\x1b, \r, \x03, \x20` を高頻度で送っていたとき、先ほどの Config Menu に自動で入ってしまい、**各プロンプトに我々の Enter がデフォルト値として吸い込まれ、全部 0.0.0.0 / 00:00:00:00:00:00 として EEPROM に書かれた**。

```
|  IP Address : 0.0.0.0                            |
|  Gateway IP : 0.0.0.0                            |
|  Subnet Mask : 0.0.0.0                           |
|  Ethernet Address : 00:00:00:00:00:00            |   ← 死亡
```

カーネルも `eth0  00:00:00:00:00:00` と MAC ゼロで起動、ifconfig は `SIOCSIFBRDADDR: Unknown error -99` で死亡。**完全にネットワーク不通**。

### 復旧 — ブートログに保存されていた MAC が活きる

幸い電源投入時の最初のブートログで正しいMAC `00:a0:66:0f:59:52` を採取していた。再度 Config Menu を ESC で呼び出して、残留 ESC 対策として各値送信前にバックスペースで入力バッファを浄化、正しい値を書き戻した。

```python
def send_value(ser, value, label):
    time.sleep(0.3)
    ser.write(b"\x08" * 20)   # 既存入力をBS連打でクリア
    time.sleep(0.3)
    ser.write(value.encode() + b"\r")
```

結果:

```
|  IP Address : 192.168.1.150                      |  ✓
|  Gateway IP : 192.168.1.1                        |  ✓
|  Ethernet Address : 00:a0:66:0f:59:52            |  ✓ 完全復活
```

カーネルログも `eth0  00:a0:66:0f:59:52` と正しい MAC に戻って ARP が通るようになった。

**教訓: 古い組込機器をいじる前にブートログは必ず全文保存する。**

## 7. LAN 探索 → Web UI 発見

ARP スキャンで一瞬で発見。

```
192.168.1.150    00-a0-66-0f-59-52 <== TARGET
ping 192.168.1.150: TTL=255 time=1ms
TCP 80: OPEN (HTTP)
```

Web UI は `ISA-httpd 0.2.2` という独自 httpd。**HTTP/0.9** (レスポンスに Status-Line が無い) で返してくる骨董品のため、curl なら `--http0.9` を付けないと弾かれる。

```html
<TITLE>DN1000警子ちゃんミニ設定ツール</TITLE>
<META HTTP-EQUIV="refresh" content="0;URL=cgi-bin/start.cgi">
```

ログイン画面は `login.cgi`。`user` と `password` の両方が **最大 8 文字** に制限されていた。

## 8. 工場出荷時パスワードを推理で特定

後継機 **DN-1500GL** のマニュアル PDF を GitHub風に漁ると、

> ```
> 工場出荷時の｢ユーザ名｣と｢パスワード｣：
> ユーザ名：DN1500
> パスワード：DN1500
> ```

**パターン = 製品型番そのまま** と判明。

DN-1000S で類推 → `DN1000 / DN1000` を投入:

```python
body = urllib.parse.urlencode({
    "user":"DN1000","password":"DN1000","login":"1","stat":"0"})
```

**🎯 一発でログイン成功**。警子ちゃんシリーズの共通の工場出荷時認証パターンだった。

## 9. rsh 制御を解析

Web UI に入れればパスワード変更やリセット等は可能だが、せっかくなので **Python から直接パトランプを制御する** API として rsh を使う。

DN-1500GL マニュアルには rsh コマンド仕様が全部載っていた:

| コマンド | 機能 |
|---|---|
| `RLY1`〜`RLY8` | リレー個別制御 (TurnOn / TurnOff / Blink) |
| `ACOP` | 8桁パターンで一括制御 |
| `ALOF` | アラーム停止 |
| `VERN` | バージョン取得 |
| `UTID` | 機器 ID |

ただし DN-1000S はファームが古く(2008年)、DN-1500GL (2012年追加) の TCP ソケット通信は未実装。 **rsh (TCP 514) だけ**。

### 特権ポート問題

BSD rsh のプロトコルは **クライアントが 1024 未満のポートから接続する** ことを要求する。普通の非特権プロセスでは Linux では bind できないが、**Windows なら非特権でも 1024 未満をbind できる**(Windowsのみ)。

```python
s = socket.socket(AF_INET, SOCK_STREAM)
s.bind(("0.0.0.0", 1023))   # ★特権ポートから発信
s.connect((host, 514))
```

source port を 1023 にしただけで接続持続 → `root/root` でコマンド投入成功。

### HELP の応答

```
acop alof ckid help lgpw pwst rly1 rly2 rly3 rly4
rly5 rly6 rly7 rly8 rops sdef utid vern
```

## 10. 完成した制御ライブラリ

```python
# dn1000s.py (抜粋)

import socket, itertools

class DN1000S:
    _port_pool = itertools.cycle(range(600, 1024))

    def __init__(self, host, remote_user="root", local_user="root", password=None):
        self.host = host
        self.remote_user = remote_user
        self.local_user = local_user
        self.password = password

    def _rsh(self, cmd, timeout=5):
        if self.password and "-p " not in cmd:
            cmd = f"{cmd} -p {self.password}"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        for _ in range(50):           # TIME_WAIT を避けて特権ポートをローテート
            try:
                s.bind(("0.0.0.0", next(self._port_pool)))
                break
            except OSError:
                continue
        s.connect((self.host, 514))
        payload = (
            "0\0"
            + self.local_user + "\0"
            + self.remote_user + "\0"
            + cmd + "\0"
        ).encode()
        s.sendall(payload)
        resp = b""
        try:
            while True:
                c = s.recv(4096)
                if not c: break
                resp += c
        except socket.timeout:
            pass
        s.close()
        return resp[1:].decode("shift_jis","replace").rstrip() \
            if resp.startswith(b"\x00") else resp.decode("shift_jis","replace")

    def lamp_on(self, n, t=None):
        cmd = f"RLY{n} TurnOn"
        if t is not None: cmd += f" -t {t}"
        return self._rsh(cmd)

    def lamp_off(self, n):     return self._rsh(f"RLY{n} TurnOff")
    def lamp_blink(self, n, w=None, t=None):
        cmd = f"RLY{n} Blink"
        if w is not None: cmd += f" -w {w}"
        if t is not None: cmd += f" -t {t}"
        return self._rsh(cmd)
    def alarm_off(self):       return self._rsh("ALOF")
    def acop(self, pattern):   return self._rsh(f"ACOP {pattern}")
    def version(self):         return self._rsh("VERN")
```

使用例:

```python
dev = DN1000S("192.168.1.150")
print(dev.version())             # "03.077.4D"
dev.lamp_on(1, t=3)              # 赤ランプを3秒点灯
dev.lamp_blink(2, w=1, t=10)     # 黄ランプを1秒周期で10秒点滅
dev.acop("10000000", t=2)        # 赤のみ2秒点灯の一括制御
dev.alarm_off()
```

## 11. ハマりどころまとめ

| 現象 | 原因と対策 |
|---|---|
| `login:` が出るのにパスワードプロンプトが出ない | μClinux の getty が /bin/login 呼出に失敗するダミーループ。シリアルユーザランド侵入は諦めて LAN 側から行く |
| CH340 ドライバが連続オープンでハング | プロセス終了後 USB を物理的に抜き差しが一番速い |
| ESC 連打で EEPROM 勝手に書き換わる | BIOS が Config Menu に遷移した瞬間に Enter キーを全部食べる。検出後は**最低 1.5 秒ドレイン**してからデータ送信 |
| IP 入力が `0.192.168.1` になる | 残留 ESC が先頭に入って octet がシフト。BSで浄化 |
| curl が `HTTP/0.9 when not allowed` | `--http0.9` オプション。ISA-httpd 0.2.2 は骨董品 |
| rsh 接続直後に切断される | source port を 1024 未満に bind しないと rsh サーバが拒否 |
| rsh の `DN1000/DN1000` で Login Incorrect | Web UI の認証とは別物。rsh のローカル認証は `root/root` で通る |

## 12. おわりに

- **古いネットワーク機器 + パスワード不明 + 製造元のサポート切れ** というよくある状況でも、シリアルコンソール → ブートローダ → EEPROM 解析 → 既知シリーズのマニュアル引用 で解ける
- **メーカー共通の命名規則** が見えるとデフォルトパスワードは推理で突破できる。逆に言うと、デフォルトパスワードを変更していない古い機器はネットワーク上で非常に危険
- 古くなった装置を延命するとき、**ブートログを全文キャプチャして MAC アドレスや IP 情報を残しておく** だけで将来の事故からかなり救われる

とはいえ、これは**自社所有機器を救出する** 前提での調査・復旧作業です。他人の機器に同じことをやると普通にアウトなので念のため。

## 参考リンク

- [株式会社アイエスエイ](https://isa-j.co.jp/)
- [警子ちゃんミニ DN-1000S 製品ページ (販売終了)](https://isa-j.co.jp/keiko/products/keikochanmini/lineup_001.html)
- [DN-1500GL 取扱説明書 PDF](http://isa-j.co.jp/dn1500gl/files/dn1500gl-manual-20150121.pdf) — 本記事の rsh 仕様の出典
- [RFC 1282 (BSD Rlogin)](https://datatracker.ietf.org/doc/html/rfc1282)
