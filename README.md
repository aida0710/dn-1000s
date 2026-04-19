# dn1000s-py

**ISA 警子ちゃんミニ DN-1000S** (生産終了のネットワーク警告灯) を Python から制御するライブラリです。

LAN 上の機器に rsh プロトコル (TCP 514) で直接コマンドを送ります。パトランプの3色 LED とブザー、ブリンク・タイマー自動OFF までサポート。依存は **Python 3.9+ の標準ライブラリのみ**。

製品の解析から復旧、ライブラリ完成までの経緯は [article.md](article.md) にまとめてあります。


| 正面 | 裏 |
|:-:|:-:|
| <img width="400" src="https://github.com/user-attachments/assets/b3287027-647e-4dff-b876-2dd986b28cb1" /> | <img width="400" src="https://github.com/user-attachments/assets/56b46963-4092-4fc3-a84b-61ba8123d747" /> |
---

## 対応機器

| 項目 | 値 |
|---|---|
| 機種 | ISA 警子ちゃんミニ DN-1000S (3Lタイプ) |
| ファーム | DN1000 v03.077.4D (2008) 以降 |
| 内蔵 OS | μClinux 2.2.14 (Samsung S3C4XXX) |
| 制御 | rsh (TCP 514) / HTTP Web UI / SNMP |

本ライブラリでは **rsh** を使います。rsh サーバーは特権ポート(<1024)からの接続を要求するため、クライアントが源ポートを 1024 未満に bind する必要があります。

- **Windows**: 非特権プロセスでも bind 可能 → 普通に動きます
- **Linux/macOS**: 特権ポート bind には `CAP_NET_BIND_SERVICE` または root 権限が必要 → `sudo python ...` または `setcap` で付与

---

## インストール

```bash
git clone <this repo>
cd dn-1000s
# Python 依存パッケージは無し (標準ライブラリのみ)
```

機器側設定が初期状態になっていれば、そのまま動きます。設定が分からなくなった場合は [qiita_article.md](article.md) の復旧手順を参照してください。

**工場出荷時の認証**:

| アクセス | ユーザー | パスワード | 備考 |
|---|---|---|---|
| Web UI (HTTP 80) | `DN1000` | `DN1000` | 型番がそのまま初期値 |
| rsh (TCP 514) | `root` | (無し) | rsh ユーザー設定で許可されていれば通る |

---

## ライブラリとしての使い方

```python
from debug_scripts.dn1000s import DN1000S

dev = DN1000S("192.168.1.150")

# 色名でアクセス
dev.red.on(t=3)  # 赤ランプを3秒点灯 (自動OFF)
dev.yellow.blink(w=1, t=10)  # 黄ランプを1秒周期で10秒点滅
dev.green.off()  # 緑ランプ消灯

# ブザー
dev.buzzer_cont.on(t=2)  # 連続ブザー 2秒
dev.buzzer_disc.on(t=2)  # 断続ブザー 2秒

# 一括制御 (ACOP: 8桁パターン)
dev.acop("10200000", t=5)  # 赤=ON, 黄=維持, 緑=Blink, 5秒後OFF

# その他
print(dev.version())  # "03.077.4D"
print(dev.unit_id())  # "1000"
print(dev.help())  # 機器がサポートするコマンド一覧

dev.all_off()  # 全チャネル停止

# 生コマンド (rsh に直接送る)
print(dev.raw("VERN"))
```

### ACOP パターンの仕様

8文字の文字列。各桁がチャネル1個に対応:

| 桁 | 対象 |
|---|---|
| 1 | 赤ランプ |
| 2 | 黄ランプ |
| 3 | 緑ランプ |
| 4 | 連続ブザー |
| 5 | 断続ブザー |
| 6-8 | 未使用 |

各桁の値:

| 値 | 意味 |
|---|---|
| `x` | 現状維持 |
| `0` | TurnOff |
| `1` | TurnOn |
| `2` | Blink |

例: `"10200000"` = 赤ON、黄維持、緑Blink、他すべてOff

### API リファレンス

```python
class DN1000S:
    def __init__(self, host, rsh_user="root", local_user="root",
                 password=None, timeout=5.0)

    # チャネル (すべて _Channel)
    .red, .yellow, .green, .buzzer_cont, .buzzer_disc
        ch.on(t=None)               # TurnOn、t秒後に自動OFF
        ch.off()                    # TurnOff
        ch.blink(w=None, t=None)    # Blink、w秒周期、t秒後に自動OFF
        ch.status()                 # TurnOn / TurnOff / Blink

    # 一括/情報
    def acop(pattern, w=None, t=None) -> str
    def all_off() -> str
    def alarm_off() -> str           # ALOF
    def version() -> str             # VERN
    def unit_id() -> str             # UTID
    def help() -> str                # HELP

    # 低レベル
    def raw(command) -> str          # 任意の rsh コマンド
```

---

## CLI としての使い方

```bash
python dn1000s.py <subcommand> ...
```

| サブコマンド | 例 |
|---|---|
| `on <ch> [-t N]` | `python dn1000s.py on red -t 5` |
| `off <ch>` | `python dn1000s.py off yellow` |
| `blink <ch> [-w W] [-t T]` | `python dn1000s.py blink green -w 1 -t 10` |
| `acop <pattern> [-w] [-t]` | `python dn1000s.py acop 22200000 -t 3` |
| `status` | 現在の3色状態 |
| `version` | ファームウェアバージョン |
| `help` | 機器サポートコマンド |
| `alloff` | 全OFF |
| `raw <cmd...>` | `python dn1000s.py raw VERN` |

共通オプション:

```
--host HOST          機器の IP (default: 192.168.1.150)
--user USER          rsh ユーザー名 (default: root)
--password PASS      rsh パスワード (PWST Enabled の場合)
```

---

## サンプルスクリプト

`examples/` ディレクトリに実用例を用意しています。

### 1. `demo_patterns.py` — パターン集

事前定義されたパターンを再生。関数として import もできます。

```bash
python examples/demo_patterns.py signal     # 信号機サイクル
python examples/demo_patterns.py sos        # SOS モールス信号
python examples/demo_patterns.py rainbow    # 赤→黄→緑 チェイス
python examples/demo_patterns.py police     # 赤⇔黄高速点滅 (パトカー風)
python examples/demo_patterns.py warning    # 3色同時点滅
python examples/demo_patterns.py countdown  # 10秒カウントダウン
python examples/demo_patterns.py all        # 全部連続実行
```

```python
# コードからも使える
from examples.demo_patterns import morse
morse(dev, "HELLO WORLD", dot=0.15)
```

### 2. `alert_on_error.py` — ログ監視

ログファイルを tail して、`ERROR|CRITICAL|FATAL` 検出で赤点滅、通常時は緑点灯。

```bash
python examples/alert_on_error.py /var/log/app.log
python examples/alert_on_error.py app.log --pattern "CRITICAL|FATAL"
python examples/alert_on_error.py app.log --alert-seconds 120
```

### 3. `http_healthcheck.py` — HTTP疎通監視

指定URLを定期的に叩き、ステータスコードに応じて色を変える。

```bash
python examples/http_healthcheck.py https://example.com/health
python examples/http_healthcheck.py https://example.com --interval 60
```

| HTTPコード | 色 |
|---|---|
| 2xx/3xx | 緑 (On) |
| 4xx | 黄 (On) |
| 5xx / 接続失敗 | 赤 (Blink) |

### 4. `webhook_server.py` — Webhook受信

HTTPサーバーを立てて、受信した webhook でパトランプを制御。

```bash
python examples/webhook_server.py                # :8080 で待受
python examples/webhook_server.py --port 9000
python examples/webhook_server.py --bind 0.0.0.0 --host 192.168.1.150
```

#### エンドポイント

**`POST /alert` — 独自JSON**

severityベース:
```bash
curl -X POST http://localhost:8080/alert \
     -H "Content-Type: application/json" \
     -d '{"severity":"critical","message":"DB down"}'
```

生指定:
```bash
curl -X POST http://localhost:8080/alert \
     -H "Content-Type: application/json" \
     -d '{"color":"yellow","mode":"blink","seconds":30}'
```

severity → 色マップ:

| severity | 色 | モード | 秒 |
|---|---|---|---|
| critical / fatal / alert | 赤 | Blink | 60 |
| error | 赤 | On | 60 |
| warning / warn | 黄 | On | 60 |
| notice | 黄 | On | 30 |
| info | 緑 | On | 10 |
| ok / resolved / recovered | 緑 | On | 5 |

**`POST /grafana` — Grafana Alertmanager**

Grafana の Contact Point に webhook を設定。`status=firing` で severity ラベルに応じた色、`status=resolved` で緑。

```bash
# Grafana 側の webhook URL 設定例:
#   http://monitoring-host:8080/grafana
```

**`POST /github` — GitHub Webhook**

リポジトリの webhook 設定 URL を `http://your-host:8080/github` に。

| イベント | 条件 | 動作 |
|---|---|---|
| `workflow_run` | conclusion=success | 緑 5秒 |
| `workflow_run` | conclusion=failure | 赤点滅 60秒 |
| `push` | — | 緑点滅 3秒 |
| `pull_request` | action=opened | 黄点滅 5秒 |
| `pull_request` | action=closed (merged) | 緑 5秒 |

**`POST /` — プレーン (クエリ文字列)**

```bash
curl -X POST "http://localhost:8080/?color=red&mode=blink&seconds=10"
```

#### フロントにリバースプロキシを置く例

nginx で HTTPS 化+経路別制御:

```nginx
location /alert {
    proxy_pass http://127.0.0.1:8080;
}
```

---

## トラブルシュート

| 症状 | 原因と対策 |
|---|---|
| `ConnectionResetError` | 源ポートが 1024 以上。Windows は自動で低ポートを使うが、既存プロセスが 600-1023 を全部押さえていると失敗。一度スクリプトを終了して再実行 |
| `rshd: Login Incorrect` | `rsh_user` 設定に無いユーザ名。`root` または Web UI の「コマンドアクセス設定」で登録したユーザ名を使う |
| `rshd: Invalid Command` | コマンド引数形式が違う。`-t 2.0` のような float ではなく整数を渡す |
| 応答が空文字 | 成功時のレスポンスがゼロ長なのは正常 (rsh は成功を NUL で示すのみ) |
| 赤黄緑は光るがブザーが鳴らない | 本体のボリュームつまみが絞られている、またはハード故障。論理的には ACOP 4/5 桁目で制御できている |
| 機器が LAN に出てこない | `arp -a` で MAC `00:a0:66:xx:xx:xx` を探す。IPが不明な場合は BIOS 経由で再設定 ([qiita_article.md](article.md) §7) |

### 特権ポート問題の詳細

```python
s = socket.socket(AF_INET, SOCK_STREAM)
s.bind(("0.0.0.0", 1023))   # ← 鍵: 源ポートを特権ポートにする
s.connect((HOST, 514))
```

- **Windows**: この bind は非特権で成功。普通にスクリプトを走らせれば OK
- **Linux/macOS**: Permission denied になる
  - 一時的: `sudo python dn1000s.py ...`
  - 永続的: `sudo setcap cap_net_bind_service=+ep $(which python3)`

---
