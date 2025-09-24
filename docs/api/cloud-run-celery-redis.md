# Cloud Run + Celery + Redis 統合レポート

**最終更新日**: 2025-09-23  
**担当**: Platform / Data Engineering

---

## 概要
- FastAPIベースの `kaboom-api` に、Redisを介したCelery分散タスク基盤を統合。
- Cloud Run上にAPIサービスとCeleryワーカーサービスを分離デプロイし、VPCアクセスコネクタ経由でCloud Memorystore (Redis) に接続。
- インジェスト系エンドポイント (`POST /api/v1/ingest/run-daily` 等) が非同期実行され、ジョブステータスはRedis上に保存される。

### 現在の稼働構成
| コンポーネント | サービス名 / リソースID | 役割 | 補足 |
| --- | --- | --- | --- |
| Cloud Run API | `kaboom-api-657734233816` | FastAPI本体 | 外向けHTTPS、Celeryへのジョブ投入 |
| Cloud Run Worker | `kaboom-celery-worker` | Celery常駐ワーカー | 内部Ingress、`celery worker` 起動 |
| Cloud Memorystore | `redis-asia-northeast1` (1GB Standard HA) | ブローカー / 結果バックエンド | Private IP: `10.94.35.116:6379` |
| VPC Access Connector | `kaboom-vpc-connector-2` | Cloud Run ↔ Redis 接続 | Region: `asia-northeast1` |
| Secret Manager | `redis-url`, `celery-broker-url`, `celery-result-backend` 他 | 接続情報保管 | バージョン `latest` を使用 |

---

## アーキテクチャ詳細
1. クライアントが `POST /api/v1/ingest/run-daily` を実行すると、FastAPIがCeleryタスク `ingest.run_daily` をキュー `ingest` に投入。レスポンスには `job_id` を返す。
2. Celeryワーカー（Cloud Runサービス）がRedisブローカーからジョブを取得し、`batch.scripts.run_daily_ingest.run_daily_ingest` を実行。実行結果/例外はRedisバックエンドに格納される。
3. FastAPIはRedisに保存したメタデータとCelery `AsyncResult` を参照し、`GET /api/v1/ingest/jobs/{job_id}` などで状態を返す。
4. Redisキー管理:
   - メタデータ: `ingest:job:{job_id}`
   - ジョブ一覧: `ingest:jobs` (LPUSH 100件保持)

---

## Cloud Run デプロイ設定
### APIサービス (既存)
- イメージ: Artifact Registry `${REGION}-docker.pkg.dev/${PROJECT_ID}/kaboom-api/${SERVICE}`
- 環境変数: `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `DISABLE_CELERY=false`, `DISABLE_REDIS=false` 等
- インスタンス: min 1 / max 5、Gen2、VPCコネクタ経由

### Celeryワーカーサービス
- マニフェスト: `api/celery-worker-service.yaml`
- 起動コマンド: `celery -A app.tasks.celery_app worker --loglevel=info --queues=ingest,ai_analysis,backtest,market_data,notifications --concurrency=4 --prefetch-multiplier=1`
- Ingress: internal（APIからのみアクセス）
- スケール設定: minScale=1, maxScale=5、CPU 2 vCPU / 4GiB
- タイムアウト: 3600秒

---

## シークレットおよび環境変数
| 項目 | Secret Manager キー | 用途 |
| --- | --- | --- |
| Redis接続URL | `redis-url` | `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| Supabase | `supabase-url`, `supabase-anon-key` | 認証連携 |
| Database | `database-url` | 取引・ポートフォリオDB |
| InfluxDB | `influxdb-host`, `influxdb-token`, `influxdb-org`, `influxdb-bucket-*` | 時系列データ連携 |
| OpenRouter API | `openrouter-api-key` | AI推論 |
| JWT Secret | `jwt-secret-key` | 認証トークン |
| Ingest Token | `ingest-api-token` | `x-ingest-token` ヘッダ照合 |

各Cloud Runサービスで同一シークレットを `latest` バージョンとして参照。更新時は新バージョン発行後、サービス再デプロイが必要。

---

## 運用・監視
- **ジョブ監視**: `GET /api/v1/ingest/jobs` / `GET /api/v1/ingest/jobs/stats`
- **Celeryヘルスチェック**: `celery -A app.tasks.celery_app inspect ping`
- **Redis監視**: Cloud Monitoring Memorystoreメトリクス (CPU利用率、接続数、メモリ)
- **ログ**: Cloud Logging で `kaboom-celery-worker` の stdout/stderr を閲覧。失敗タスクはログレベルERRORで出力。
- **アラート推奨**:
  - Redis CPU > 70% (5分連続)
  - Celeryワーカーエラー1分当たり > 5件
  - Cloud Run コンテナ再起動率異常

---

## テスト手順
```bash
curl -X POST "https://kaboom-api-657734233816.asia-northeast1.run.app/api/v1/ingest/run-daily" \
  -H "Content-Type: application/json" \
  -H "x-ingest-token: <SECRET>" \
  -d '{"intervals": {"1m": 1}, "market": "TSE_PRIME", "chunk_size": 500}'

# 応答例：{"job_id":"dc84d88371794773b929d2957f6a663b","status":"queued"}

curl -H "x-ingest-token: <SECRET>" \
  "https://kaboom-api-657734233816.asia-northeast1.run.app/api/v1/ingest/jobs/dc84d88371794773b929d2957f6a663b"
```

---

## CI/CD とデプロイフロー
1. GitHub Actions `deploy.yml` が `main` ブランチ push で起動。
2. API用Cloud Runサービスへ自動ビルド & デプロイ。
3. 同ビルドイメージを `envsubst` で差し込んだ `api/celery-worker-service.yaml` に反映し、`gcloud run services replace` でワーカーサービスへ反映。
4. Secret Manager・VPCコネクタ・サービスアカウントは事前に構成済みであることが前提。

**追加設定案**
- ステージング環境の導入時は `push` ブランチ条件に `release/*` や `staging` を追加し、環境ごとにサービス名・Secretを切り替える。
- Artifact Registry のリポジトリをAPI/ワーカーで分離し、権限最小化を図る。
- Pipeline 完了後に `celery -A app.tasks.celery_app inspect ping` を実行するSmokeテストステップを追加。

---

## 今後のTODO
- Flower導入や独自ダッシュボードでジョブ状態を可視化。
- Redisクラスタ構成の検討（スループット増に備える）。
- IaC (Terraform) 化によりCloud Run/Redis/Secret構成をコード化。
- n8nワークフローとCeleryタスクのE2Eテスト自動化。

---

## 参考リンク
- Cloud Run サービス: `https://console.cloud.google.com/run?project=kaboom-472705`
- Cloud Memorystore: `https://console.cloud.google.com/memorystore/redis/instances?project=kaboom-472705`
- Secret Manager: `https://console.cloud.google.com/security/secret-manager?project=kaboom-472705`
