# Kaboom データ取得パイプライン Runbook

## 1. 目的
- 東証銘柄の株価データを yfinance から取得し、InfluxDB Cloud Serverless に保存するまでの手順をまとめる。
- 運用担当がバケット構築・トークン発行・ローカル動作確認を迷わず実施できるようにする。

## 2. 事前準備
1. **InfluxDB Cloud Serverless アカウント作成**
   - https://cloud2.influxdata.com/ でサインアップ。
   - 利用リージョン（例: `us-east-1-1`）と組織名をメモ。
2. **CLI セットアップ（任意）**
   - `brew update && brew install influxdb-cli@2` などで CLI を用意。
   - `influx config create --config-name kaboom --host https://<region>.aws.cloud2.influxdata.com --org <org> --token <token>` を実行し接続確認。

## 3. バケット作成
InfluxDB Cloud のダッシュボードで以下のバケットを作成する。

| バケット名 | 用途 | 保持期間 |
|-------------|------|----------|
| `raw_1m_hot` | 最新 1 分足データ | 365 日 |
| `raw_1m_backfill` | 有償データ等の長期 1 分足 | 無期限 |
| `agg_5m` | 5 分足 OHLCV | 180〜365 日 |
| `agg_1d` | 日足 OHLCV | 5 年 |

> **Retention 設定**: Usage プランであれば任意設定可能。Free プランは 30 日固定のため Usage へアップグレードが必要。

## 4. API トークン発行
1. ダッシュボード左側メニューの **API Tokens** を開く。
2. **Generate API Token** → **All-Access Token**（または対象バケット Write/Read）を選択。
3. 表示されたトークンを安全なパスワードマネージャに保管。
4. ローカル検証では `batch/.env.local` に `INFLUXDB_TOKEN` として記載し、Git 管理下に置かない。

## 5. ローカル環境の設定
1. `cp batch/.env.example batch/.env.local`
2. 次の値を設定:
   ```env
   INFLUXDB_HOST="https://<region>.aws.cloud2.influxdata.com"
   INFLUXDB_ORG="<your-org>"
   INFLUXDB_TOKEN="<api-token>"
   ```
3. 必要に応じてバケット名・バッチサイズを変更。

## 6. 依存関係の同期 (`uv` 利用)
Kaboom プロジェクトでは Python 依存関係管理に `uv` を採用する。

```bash
# ルートから実行
cd /Users/kazusa/Develop/kaboom/api
uv sync        # pyproject.toml / uv.lock に基づき環境を構築
```

## 7. バックフィルの実行
```bash
cd /Users/kazusa/Develop/kaboom
uv run --project api python -m batch.ingest.backfill_yf \
  --symbols 7203.T 9984.T --days 30 --interval 1m

# 5分足を60日分取得し、agg_5mバケット (measurement: ohlcv_5m) に保存
uv run --project api python -m batch.ingest.backfill_yf \
  --symbols 7203.T 9984.T --days 60 --interval 5m

# 日足を2年分取得し、agg_1dバケット (measurement: ohlcv_1d) に保存
uv run --project api python -m batch.ingest.backfill_yf \
  --symbols 7203.T 9984.T --days 730 --interval 1d
```

- `uv run --project api` で `api/pyproject.toml` に定義した環境を利用しつつ、リポジトリ直下の `batch` モジュールを実行できる。
- 書き込み先バケットを変更したい場合は `--bucket agg_5m` のようにオプションを指定。
- interval に応じてデフォルトの書き込み先バケットと measurement（1m→`raw_1m_hot`/`ohlcv_1m`、5m 系→`agg_5m`/`ohlcv_5m` など）が切り替わる。
- yfinance の仕様上、1 分足はリクエストあたり 7〜8 日までしか取得できないため、スクリプト内部で期間を自動分割して取得する。また 1 分足の履歴は過去 30 日未満しか取得できないため、`--days` を指定しても上限は自動的に約 29 日にトリミングされる。5 分足は約 60 日、日足は最大 5 年程度までを想定している。

## 8. 結果確認
1. 実行ログで書き込み件数を確認。
2. InfluxDB の **Data Explorer** で `raw_1m_hot` バケットを開き、対象銘柄のデータが存在するか確認。
3. 必要に応じて `SELECT` クエリまたは InfluxDB Studio のグラフで検証。

## 9. トラブルシューティング
- **401 Unauthorized**: トークンの権限不足。All-Access または対象バケット Write 権限を再付与。
- **Rate limit**: yfinance の制限に達した場合は `--sleep` オプションを追加しリクエスト間隔を延長。
- **タイムゾーン不一致**: 取得データは JST、InfluxDB は UTC タイムスタンプで保存。スクリプト内で `tz_convert('UTC')` 済み。
- **依存が同期されない**: `uv sync --project api --refresh` で再解決。

## 10. 今後の拡張
- JPX 有償データ取り込み時は `batch/ingest/backfill_jpx.py` を実装し、`raw_1m_backfill` に書き込む。
- 集計ジョブ（1 分→5 分/日足）を `batch/pipeline/downsample_sql.py` に実装し、Cron で運用。
- 監視用メトリクス・アラートは `monitor/checks.py` に追加し、運用ダッシュボードと連携する。
