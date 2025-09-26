# 売買判断向けAPI設計サマリ

本書では、売買判断フローを支えるAPI群を整理し、ジョブ構成や依存関係を明確化する。各APIはFastAPIを前提とし、Cloud Tasks／Redisによる非同期実行と状態管理を基本パターンとする。

## 1. 日次バッチ（マーケットデータ基盤）

| APIカテゴリ | エンドポイント例 | 概要 | 主な入出力 |
|-------------|------------------|------|------------|
| 市場データ取得ジョブ | `POST /api/v1/ingest/run-daily`<br>`POST /internal/ingest/run-daily` | 1分足・5分足・日足を対象銘柄分まとめて取得し、インフラDB（Influx/BigQuery等）へ保存。Cloud Tasksジョブ化。 | 入力: 対象市場、対象銘柄リスト、取得期間。<br>出力: `job_id`、進行状況。 |
| ジョブステータス | `GET /api/v1/ingest/jobs/{job_id}` | Redisに蓄積されたジョブ状態を返却。 | 出力: `status`, `progress`, `message`, `result_uri` 等。 |
| データ品質チェック | `POST /internal/ingest/validate` | 欠損データ・異常値を検知し、補完処理やアラートを生成。 | 出力: 異常レポート、補完フラグ。 |

## 2. トレード判断フロー（毎分実行）

| ステップ | APIカテゴリ | エンドポイント例 | 説明 |
|----------|-------------|------------------|------|
| ユニバース銘柄選定 | ユニバース管理API | `POST /api/v1/universe/run-selection`<br>`GET /api/v1/universe/current` | ファンダ・流動性条件に基づき対象銘柄リストを更新。ジョブはCloud Tasks化し、結果をRedis/DBに保存。 |
| 足データ更新検知 | マーケット監視API | `POST /internal/market-data/on-tick` | 外部ストリームからの更新通知をトリガーに、対象銘柄の最新足をフェッチ。 |
| チャート画像生成 | チャートサービスAPI | `POST /api/v1/charts/generate` | 1分足・5分足・日足のPNG/HTMLチャートを生成し、ストレージへ保存。内部ジョブとして並列化。 |
| チャート画像分析 | ビジュアル分析API | `POST /internal/charts/analyze` | 生成済みチャートをVisionモデルで解析し、レジサポ・エントリーポイント・クローズポイント候補を抽出。 |
| テクニカル指標計算 | テクニカル指標API | `POST /api/v1/indicators/batch` | SMA、EMA、RSI、MACD、ボリンジャーバンド等をマルチ銘柄・複数タイムフレームで計算。 |
| テクニカル分析 | 分析コンポーザAPI | `POST /internal/analysis/technical` | テクニカル指標とチャート分析結果を統合し、売買シグナル候補を生成。条件式は戦略設定から取得。 |
| 総合判断 | 戦略シグナルAPI | `POST /api/v1/signals/evaluate` | テクニカル・ビジュアル・ファンダメンタル等のスコアを統合し、エントリー/見送りを判定。結果はRedisキューへ。 |
| エントリー実行 | 注文実行API | `POST /internal/orders/submit` | ブローカーAPIをラップし、約定・訂正・取消を管理。リスク管理APIと連携して最終承認。 |

補助API:
- **戦略設定API**: `POST/GET /api/v1/strategies` で指標期間・許容リスク等をCRUD。評価APIから参照。
- **リスク管理API**: `POST /api/v1/risk/check` でポジション・余力・最大ポジションサイズなどを検証。エントリー実行前に必須。
- **ジョブステータス監視API**: 分析・チャート生成ジョブの進捗を`GET /api/v1/jobs/{job_id}`で取得。

## 3. ポジションごとのトレード判断

| APIカテゴリ | エンドポイント例 | 内容 |
|-------------|------------------|------|
| ポジション取得API | `GET /api/v1/portfolio/positions` | 現在のポジション、平均取得価格、評価損益を返す。 |
| クローズポイント判定 | `POST /api/v1/signals/manage-position` | 既存ポジションに対してトレーリング、利確、損切ラインを再計算し、保持/部分決済/全決済を判定。 |
| クローズ実行 | `POST /internal/orders/close-position` | 判定結果に従い実際の決済注文を送信。 |
| リスク・コンプライアンス監視 | `POST /api/v1/risk/monitor-position` | 含み損益や証拠金維持率をモニタリングし、閾値超過でアラート。 |

## 4. レポート・ナレッジ記録

| APIカテゴリ | エンドポイント例 | 内容 |
|-------------|------------------|------|
| トレードレポート作成 | `POST /api/v1/reports/trades` | トレードごとの判断材料（チャート解析結果、指標値、エントリー理由、反省点）を保存。 |
| レポート取得 | `GET /api/v1/reports/trades/{trade_id}` | 保存済みレポートの詳細取得。画像・指標ログへの参照含む。 |
| アラート通知API | `POST /internal/alerts/publish` | 売買判断結果、リスクイベント、レポート更新をSlack/LINEなどへ送信。 |
| 分析ナレッジベース | `POST /api/v1/knowledge/notes` | シグナル生成時のAIコメントや改善メモを蓄積し、次回判断に活用。 |

## 5. 共通基盤・監視

- **認証・認可API**: 内部エンドポイントはサービス間トークンまたはOIDCで保護。`POST /internal/auth/verify` 等を共通化。
- **ジョブスケジューラ連携**: Cloud Scheduler → Cloud Tasks → FastAPI internal endpoint の構成。ジョブ登録API `POST /api/v1/scheduler/jobs` を用意して柔軟にスケジュール変更可能にする。
- **メトリクス／ロギングAPI**: `GET /api/v1/monitoring/metrics` でジョブ成功率、平均レイテンシを可視化。失敗ログはStackdriver連携。

## 6. 今後の拡張ポイント

1. **バックテストAPI**: `POST /api/v1/backtest/run` で新戦略を検証し、ライブ戦略へ昇格する際のゲートとして利用。
2. **シミュレーションAPI**: 想定注文に対するスリッページ、手数料、必要証拠金を事前計算 (`POST /api/v1/orders/simulate`)。
3. **AIアシスタントAPI**: 判断根拠説明を自然言語で生成し、レポートAPIに添付する (`POST /api/v1/ai/explain-trade`)。
4. **リプレイAPI**: 過去の市場データをストリーミングし、リアルタイム判断ロジックのテストに活用 (`POST /api/v1/market/replay`)。

---

これらのAPI群を順次実装することで、データ取得・解析・判断・実行・振り返りまで一貫した売買判断プラットフォームが構築できる。各APIはCloud Tasksを活用した非同期化とRedisベースのジョブトラッキングを徹底し、FastAPIのサービス層にドメインロジックを集約する方針とする。
