# API実装の優先検討事項

KaboomのFastAPIコードベースを確認した上で、売買判断フローのAPIを段階的に整備するために優先して着手すべき項目を整理する。既存実装の状況と依存関係を踏まえて、最初の開発イテレーションで実現すべき範囲を明確化する。

## 1. 現状把握

- **データインジェストはCloud Tasksに移行済み**: `/api/v1/ingest/run-daily` はCloud Tasksクライアントを使い、内部エンドポイント `/internal/ingest/run-daily` が実行本体を担う構成になっている。ジョブ進捗はRedis経由で `JobProgressService` が管理する。既に非同期ジョブ基盤のリファレンス実装として利用できる。 
- **ジョブ進捗APIは共通化済み**: `/api/v1/jobs/*` で進捗・統計を参照でき、`JobProgressService` が`queued/running/completed/failed`を扱う汎用ロジックを提供している。新ジョブもこの仕組みに統合すべき。 
- **ユニバース選定はCLIバッチに留まる**: `api/batch/pipeline/select_universe.py` でCLIとして完結しており、FastAPIルーターやCloud Tasksエントリポイントは未実装。売買判断フローの上流に位置するため、最優先でAPI化する必要がある。 
- **テクニカル指標はサービス層のみ**: `MarketDataService.get_technical_indicators` が複数指標を計算するが、バッチ計算や戦略向けのAPIはまだ。チャート生成・分析APIも未着手で、後続フロー（戦略シグナル生成）には未整備箇所が多い。

## 2. 優先実装ステップと順番の理由

実装順序を安定性と手戻りの少なさの観点から再検討すると、以下の4段階が最も効率的である。

1. **下支えとなるサービス層の抽出**: CLI専用の処理をサービス化し、FastAPIやCelery/Cloud Tasksから共通利用できるようにする。
   - *理由*: 依存するバッチロジックのテスタビリティを確保し、API実装時に重複コードやI/Oの副作用を避けられる。以降のステップの土台。
2. **ユニバース選定ジョブのCloud Tasks化**: パブリック／内部APIを整備し、ジョブ進捗・結果管理をJobProgressServiceに統合する。
   - *理由*: 売買判断フローの上流にあり、他API（指標計算・分析）が依存するデータ供給源。先に安定稼働させることで後続の負荷や障害範囲を限定できる。
3. **テクニカル指標バッチAPIの整備**: Universe選定結果を入力にした指標計算を提供し、戦略や可視化から再利用可能にする。
   - *理由*: チャート／AI分析の前提データとなるため、Universe選定API完成後に取り掛かるのが自然。キャッシュやタイムアウト制御もこの段階で整備する。
4. **チャート生成〜AI分析ジョブの骨格構築**: 画像生成と分析を段階的にクラウドタスク化し、複数ステップのジョブ管理を検証する。
   - *理由*: 前段が安定したデータ供給を保証した上で、段階的に高度な処理へ進む。AI部分はスタブ化し、将来のモデル差し替えを容易にする。

以下では各ステップの詳細タスクを整理する。

### ステップ1: サービス層の抽出と共通ユーティリティ整備

1. **UniverseSelectionServiceの新設**: `select_universe.py` のロジックからI/Oを分離し、引数で対象銘柄や設定を受け取り結果オブジェクトを返すよう実装する。
2. **CLIの移行**: 既存CLIをサービス層経由で動かすようリファクタリングし、CSV入出力だけを担う薄いラッパーへ置き換える。
3. **テスト可能な構造の確立**: 上記サービスに対するユニットテスト（モック済みのInflux/Supabaseクライアント）を追加し、将来のAPI実装でも流用できるフィクスチャを用意する。UniverseSelectionService向けのテストは `api/tests/services/test_universe_selection_service.py` として整備済みで、Cloud Tasks連携の正常系と検証パスをカバーしている。

### ステップ2: ユニバース選定ジョブのCloud Tasks化

1. **パブリックエンドポイントの追加**: `/api/v1/universe/run-selection` でCloud Tasksへジョブ投入し `job_id` を返却する。既存インジェストAPIの構造を再利用する。
2. **内部エンドポイントの実装**: `/internal/universe/run-selection` で新設した `UniverseSelectionService` を呼び出し、Redisへ進捗を記録する。`JobProgressService` と `IngestPayload` 相当のPydanticモデルを用意し、ジョブIDや対象銘柄リスト、スコア結果URIなどをメタデータとして保存する。
3. **結果・ストレージ設計**: 選定結果（core/benchリスト）とスコアスナップショットをGCSやSupabaseへ配置する場合はURIを返すようにし、ジョブ完了時に `set_job_result` を呼ぶ。
4. **n8n統合と認証**: 新ジョブも `X-Universe-Token` などの専用トークンを設け、Cloud Tasks IAM検証を `_verify_cloud_tasks_request` 相当の関数で共通化する。

### ステップ3: テクニカル指標バッチAPIの整備

1. **バッチリクエスト用ルーター**: `POST /api/v1/indicators/batch` を実装し、銘柄リストとタイムフレームを受け取って `MarketDataService` を並列実行する。結果はRedisキャッシュとCloud Storage保存の両方を選択できるようにする。
2. **キャッシュ＆失敗ハンドリング**: `MarketDataService` が単銘柄向けキャッシュを持つため、バッチ処理時のキャッシュキー設計とタイムアウト制御を追加する。エラー銘柄はジョブ結果の `failed_symbols` としてまとめる。
3. **戦略設定との連携準備**: 指標パラメータ（期間、閾値）を戦略設定から取得する仕組みを見越し、`strategies` テーブルや設定APIへの依存点を整理する。

> このステップ完了で、チャート生成や分析APIからも再利用できるテクニカル指標計算の土台ができる。Universe選定後の候補銘柄に限定して呼び出すことで負荷を抑えられる。

### ステップ4: チャート生成〜AI分析ジョブの骨格構築

1. **チャート生成タスク**: Matplotlib/Plotly等を使って指定銘柄・タイムフレームのチャート画像/HTMLを生成する内部タスクをCloud Tasks化する。結果はCloud Storageに保存し、URLをジョブ結果に含める。
2. **ビジュアル分析タスクのスタブ**: 生成済みチャートをVisionモデルで分析する内部エンドポイントを作り、現時点ではダミーのスコアや注釈を返す。後でAIモデルが準備できた際に差し替えやすくする。
3. **ジョブ連携フロー**: チャート生成完了後に分析タスクをチェーン実行する仕組み（Cloud Tasksの遅延タスク、または内部でのサブタスク起動）を検討し、ジョブ進捗サービスで複数ステップをトラッキングできるようにする。

> この段階では最終的なシグナル判定までは踏み込まず、データ生成と解析結果の蓄積基盤を整えることを目標とする。Universe選定と指標計算が整っていれば、必要銘柄数を限定したバッチ処理が可能になる。

## 3. 補足検討事項

- **ジョブ進捗サービスの共通化**: `internal.py` のCloud Tasksリクエスト検証ロジックをヘルパー化し、ユニバース選定・チャート生成などでも再利用する。エラー時の`set_job_error`呼び出しや例外の扱いを統一する。
- **設定・シークレット管理**: ユニバース選定で参照するSupabase/Influx設定、チャート生成で使う外部APIキーなど、`.env`のキー名と設定クラスへの追加を洗い出す。
- **テスト計画**: サービス層を先に切り出すことで、FastAPIルーターを介さないユニットテスト（pytest + async）を記述しやすくする。Cloud Tasksのキュー投入は`USE_CLOUD_TASKS=false`時に同期実行へフォールバックできるようにしておく。GitHub Actionsの`Run API tests`ワークフローでPR時にpytestが自動実行され、ユニバース選定サービスのテストが常に検証されるようになった。

---

まずはステップ1を完了させることで、ユニバース選定ロジックがサービス層として再利用可能になり、FastAPI・Cloud Tasksから呼び出す際の副作用を抑えられる。ステップ2以降はこの土台を活用してAPI化とジョブ管理の強化を進め、データ供給→指標計算→可視化・分析の順で機能を積み上げていく想定である。

## 4. 実装TODOチェックリスト

- [x] ステップ1-1: UniverseSelectionServiceを追加し、CLIロジックからビジネス処理を分離する。
- [x] ステップ1-2: CLIを新サービス経由で実行するようリファクタリングし、CSV入出力処理を薄く保つ。
- [x] ステップ1-3: UniverseSelectionServiceのユニットテストを追加して主要パスを検証する（Cloud Tasks投入の正常系と入力バリデーション、設定エラーを含む）。
- [ ] ステップ2-1: `/api/v1/universe/run-selection` を実装してCloud Tasksへジョブを投入する。
- [ ] ステップ2-2: `/internal/universe/run-selection` を実装し、JobProgressServiceとの連携を整える。
- [ ] ステップ2-3: Universe選定結果のストレージ設計とジョブ結果メタデータの保存を行う。
- [ ] ステップ2-4: 認証・n8n統合を共通ヘルパー化し、Cloud Tasks検証ロジックを再利用する。
- [ ] ステップ3: テクニカル指標バッチAPIを整備し、キャッシュ／失敗ハンドリングを実装する。
- [ ] ステップ4: チャート生成〜AI分析ジョブを段階的にCloud Tasksへ移行し、マルチステップ進捗管理を実現する。

### ステップ2の詳細設計と着手順

#### ステップ2-1 `/api/v1/universe/run-selection` の設計

- **ルーター配置**: `api/app/routers/universe.py` を新設し、`APIRouter(prefix="/api/v1/universe", tags=["Universe"])` を宣言。`api/app/routers/__init__.py` と `app/main.py` でルーター登録を行う。インジェストAPIと同様に `settings.USE_CLOUD_TASKS` のフラグで同期実行フォールバックを切り替える。
- **リクエストモデル**: `UniverseSelectionRequestBody`（Pydantic）を定義し、以下を受け取る。
  - `market`: 省略時 `"TSE_PRIME"`。
  - `symbols`: 任意の明示リスト。指定時はSupabaseクエリをスキップ。
  - `existing_core`: 直近のコア銘柄リスト。
  - `thresholds_override`: 閾値上書き辞書。
  - `settings_path`: CLIと同じ設定YAMLへの相対パス（デフォルトは `batch/config/universe.yml`）。
- **レスポンスモデル**: `UniverseSelectionJobResponse` として `job_id` / `status` / `requested_at` を返す。Cloud Tasks無効時は `result_preview` として `core` / `bench` の先頭数件を含める形で同期レスポンスを返し、フロント/オペレーションからの即時検証を可能にする。
- **Cloud Tasks投入処理**:
  - `CloudTasksClient.enqueue_http_task` を利用し、`/internal/universe/run-selection` にPOST。payloadは `job_id`・`created_at`・`payload`（内部用パラメータ）をラップした `CloudTaskPayload` 形式に揃える。
  - `payload` 内には UniverseSelectionService へ渡す `settings_path` / `market` / `symbols` / `existing_core` / `thresholds_override` を含む。`executor="cloud_tasks"` を明示してJobProgressServiceでの判定に使う。
  - Redisの `universe:job:<job_id>` へ依頼メタデータを保存するためのヘルパー（`_store_universe_job_metadata`）を実装し、`JobProgressService.create_job` で `job_type="universe_selection"` を設定する。

#### ステップ2-2 `/internal/universe/run-selection` の実装方針

- **共通ペイロードスキーマ**: `CloudTaskPayload` と対になる `UniverseSelectionTaskPayload` を `internal.py` に定義。`settings_path` などは `UniverseSelectionService.UniverseSelectionRequest` へそのまま渡せるキーにする。
- **処理フロー**:
  1. `_verify_cloud_tasks_request` を再利用（後述のヘルパー化の対象）。
  2. `JobProgressService.create_job` → `status=RUNNING` 更新までは日次インジェストの流れを踏襲。`total_steps` は暫定で `5`（`symbol_load`/`metrics`/`filter`/`scoring`/`persist`）としておき、各段階で `progress_percent` と `current_step` を更新する。
  3. `UniverseSelectionService.run_selection` を同期I/Oとして実行するため、`BackgroundTasks` + `asyncio.to_thread`（または `run_in_executor`）でCPUバウンド処理を隔離する。
  4. 成功時は `set_job_result` に以下の構造体を保存。
     ```json
     {
       "core": ["6501", "6594", ...],
       "bench": ["7203", ...],
       "snapshot_uri": "gs://kaboom-universe/2024-09-12/core.csv",
       "statistics": {
         "total_symbols": 742,
         "filtered_symbols": 136,
         "applied_thresholds": {"adv_jpy_min": 3.5e7, ...}
       }
     }
     ```
  5. 失敗時は `UniverseSelectionError` を捕捉して `set_job_error`。例外メッセージと `failed_step`（最後に更新した `current_step`）をエラー詳細に含める。
- **ロギング**: `logger = logging.getLogger("app.routers.universe")` を使用し、`job_id` と `current_step` を各ログ行に含める。n8n側のトラッキングで利用できるよう `progress_service.publish_status` も忘れず呼ぶ。

#### ステップ2-3 ストレージおよびメタデータ保存

- **出力ファイル構造**:
  - `gs://<bucket>/universe/{job_id}/core.csv`
  - `gs://<bucket>/universe/{job_id}/bench.csv`
  - `gs://<bucket>/universe/{job_id}/snapshot.parquet`
  - Supabaseテーブル `universe_snapshots` にも `job_id` / `core_count` / `bench_count` / `created_at` を保存（後続のダッシュボード向け）。
- **保存ユーティリティ**: `api/app/services/storage.py`（新設）に `store_universe_snapshot(result: UniverseSelectionResult, job_id: str) -> StoredUniverseArtifacts` を実装。GCSクライアントは `google.cloud.storage`、Supabaseは既存の `SupabaseClient` を利用。テストでは `LocalFileSystem` と `fakeredis` を使って代替。
- **JobProgressServiceメタデータ**: `set_job_result` の `result_data` に GCS URI / SupabaseレコードID を含め、`metadata` フィールドには `market` / `symbols_count` / `executor` / `artifact_bucket` などを保持する。

#### ステップ2-4 認証とn8n統合

- `_verify_cloud_tasks_request` を `api/app/routers/internal_common.py`（仮称）へ切り出し、インジェストとユニバース両タスクからインポートする。将来的に `X-Internal-Token` のバリデーションやプロジェクトIDチェックを追加しても一箇所で済むようにする。
- `settings.UNIVERSE_API_TOKEN` を追加し、パブリックAPIで `X-Universe-Token` ヘッダーを必須化。n8nのHTTP Nodeから付与する形に変更。
- Job進捗のポーリングは既存の `/api/v1/jobs/{job_id}` を活用する想定だが、n8nから参照する際に必要な `job_type=universe_selection` でのフィルタリングAPIが無いため、`/api/v1/jobs` のクエリパラメータに `job_type` を追加するタスクを別途Issue化する。
- ドキュメント整備: n8n向けRunbook（`docs/automation/universe-selection.md`）を作成し、HTTPノード設定例とトークン管理ポリシーを記載する。ステップ2完了のDefinition of Doneに含める。

> 上記4項目が完了すると、ユニバース選定が日次インジェストと同じ非同期ジョブ基盤で運用できるようになる。以降のステップ3/4ではここで得た成果物（GCS URIやSupabaseレコード）を前提にテクニカル指標計算やAI分析を順次拡張していく。
