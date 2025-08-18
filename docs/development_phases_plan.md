# 株式自動売買管理システム - 開発フェーズ計画書

## 1. プロジェクト概要

### 1.1 システム構成
- **フロントエンド**: Next.js 15 + React 19 (web/)
- **バックエンド**: FastAPI + Python 3.12 (api/)
- **共通**: Supabase (認証・データベース)、Redis、WebSocket

### 1.2 開発方針（改訂版）
- **UIファースト開発**: サンプル実装を活用してUIを先行開発
- フェーズごとのブランチ戦略（feature/phase-X-XXX）
- モックデータで動作確認後、段階的にバックエンド統合
- チェックリスト形式による進捗管理

### 1.3 サンプル実装の活用
- `docs/kaboom-sample.jsx`のコンポーネントを最大限活用
- デザインシステムとUIパターンをそのまま移植
- モックデータとリアルタイムシミュレーションの利用

---

## 2. フロントエンド開発フェーズ (web/)

### Phase 1: プロジェクト基盤構築（UIファースト）- 1日

#### 1.1 環境セットアップ
- [ ] Next.js 15プロジェクト初期化（npx create-next-app@latest）
- [ ] TypeScript設定 (tsconfig.json)
- [ ] Tailwind CSS設定 (tailwind.config.ts)
- [ ] ESLint/Prettier設定
- [ ] パッケージ依存関係インストール
  - [ ] Next.js 15、React 19
  - [ ] Recharts、lightweight-charts
  - [ ] lucide-react（アイコン）
  - [ ] @supabase/supabase-js、@supabase/ssr（Phase 3で使用）

#### 1.2 サンプル実装の移植
- [ ] kaboom-sample.jsxのコード分析
- [ ] デザインシステム（CSS変数）の移植
- [ ] 基本ディレクトリ構造作成
  - [ ] src/app/ (App Router構造)
  - [ ] src/components/ (サンプルから抽出)
  - [ ] src/hooks/ (カスタムフック)
  - [ ] src/lib/ (utils、mock-data)
  - [ ] src/styles/ (グローバルCSS)

#### 1.3 ブランチ作成
- [ ] feature/phase-1-project-setupブランチ作成
- [ ] 初期コミット

**完了条件**: Next.jsプロジェクトが起動し、基本的なデザインシステムが動作する

---

### Phase 2: デザインシステム実装 - 1日 ✅

#### 2.1 デザインシステム移植
- [x] CSS変数システムの実装（ライト/ダークテーマ）
- [x] useThemeフックの実装
- [x] グローバルCSSの設定（Tailwind CSS v4対応）
- [x] PostCSS設定とTailwind設定の調整
- [x] @themeディレクティブによるカスタムカラー定義

#### 2.2 共通コンポーネント作成
- [x] Navbar.tsx（サンプルから移植、テーマ切替機能付き）
- [x] icons.tsx（lucide-reactベースのアイコンシステム）
- [x] Card.tsx（kb-card）
- [x] Button.tsx（kb-btn）
- [x] Input.tsx（kb-input）
- [x] Badge.tsx（kb-badge）
- [x] Pill.tsx（選択可能なタグ）
- [x] モックデータとユーティリティ関数

#### 2.3 レイアウト構造
- [x] RootLayout（app/layout.tsx）
- [x] テーマプロバイダーの実装
- [x] ページ遷移の基本構造
- [x] 完全機能ダッシュボードの実装

#### 2.4 ダッシュボード機能実装
- [x] SummaryCards（リアルタイム数値更新）
- [x] PortfolioChart（Recharts使用、インタラクティブ）
- [x] RealtimeTable（ソート・フィルタ・モーダル機能）
- [x] リアルタイムデータシミュレーション
- [x] WebSocketモック機能（タブ同期対応）

**完了条件**: デザインシステムとダッシュボードが完成し、テーマ切り替えとリアルタイム機能が動作する ✅

**技術的成果**:
- Tailwind CSS v4との完全互換性確保
- 参考コードベースからの洗練されたUIシステム移植
- リアルタイム更新とインタラクティブ機能の実装

---

### Phase 3: 認証UI実装（モック）- 0.5日 ✅ **完了済み**

#### 3.1 認証画面作成（UIのみ）
- [x] (auth)ルートグループ作成 - 認証専用レイアウトで美しいUI
- [x] ログイン画面UI (login/page.tsx) - デモアカウント情報付き
- [x] 新規登録画面UI (signup/page.tsx) - パスワード確認機能付き
- [x] モック認証フロー - 完全なフォームバリデーション（Zustand使用）

#### 3.2 認証状態管理（モック）
- [x] Zustandによる認証状態管理 - 永続化対応
- [x] Next.js 15 middlewareによるルート保護
- [x] ログイン/ログアウトの画面遷移
- [x] Navbarに認証情報とドロップダウンメニュー統合

#### 3.3 実装されたファイル
- `web/src/app/(auth)/layout.tsx` - 認証専用レイアウト
- `web/src/app/(auth)/login/page.tsx` - ログインページ  
- `web/src/app/(auth)/signup/page.tsx` - 新規登録ページ
- `web/src/components/AuthForm.tsx` - 認証フォームコンポーネント
- `web/src/lib/auth-store.ts` - Zustand認証ストア
- `web/src/middleware.ts` - ルート保護ミドルウェア
- `web/src/components/ClientProvider.tsx` - クライアントサイド初期化

**完了条件**: ✅ 認証UIが完全に動作し、モック認証で画面遷移が正常動作
- デモアカウント: demo@kaboom.ai / demo123
- ユーザー名表示、ログアウト機能、ルート保護すべて動作確認済み

---

### Phase 4: ダッシュボード画面実装 - 1日

#### 4.1 ダッシュボードコンポーネント
- [ ] SummaryCards.tsx（サンプルから移植）
- [ ] PortfolioChart.tsx（サンプルから移植）
- [ ] RealtimeTable.tsx（サンプルから移植）
- [ ] useRealtimeNumbersフック（モックデータ）

#### 4.2 ダッシュボードページ
- [ ] (dashboard)ルートグループ作成
- [ ] dashboard/page.tsx作成
- [ ] レイアウトの適用
- [ ] ナビゲーションの動作確認

#### 4.3 チャートライブラリの設定
- [ ] Rechartsのインストールと設定
- [ ] チャートコンポーネントの動作確認
- [ ] モックデータでの表示テスト

**完了条件**: ダッシュボード画面が完成し、モックデータで動作確認できる

---

### Phase 5: AI分析画面実装 - 1日

#### 5.1 AI分析コンポーネント
- [ ] AutoSignalHeader.tsx（サンプルから移植）
- [ ] LightweightPriceChart.tsx（lightweight-charts使用）
- [ ] FallbackPriceChart.tsx（Recharts代替）
- [ ] EvidencePanel.tsx（根拠表示）
- [ ] RiskPanel.tsx（リスク管理）

#### 5.2 AI分析ページ
- [ ] ai-analysis/page.tsx作成
- [ ] モックAI判断データの作成
- [ ] lightweight-chartsの設定
- [ ] テクニカル指標のモック表示

#### 5.3 チャート機能
- [ ] ローソク足チャートの実装
- [ ] 価格ライン（エントリー、ストップ、利確）
- [ ] マーカー表示（売買シグナル）

**完了条件**: AI分析画面が完成し、モックデータでチャートが動作する

---

### Phase 6: バックテスト画面実装 - 1日

#### 6.1 バックテストコンポーネント
- [ ] BacktestForm.tsx（設定パネル）
- [ ] BacktestProgress.tsx（進捗表示）
- [ ] BacktestResults.tsx（結果表示）
- [ ] TradeHistoryTable.tsx（取引履歴）
- [ ] HeatmapChart.tsx（月別収益）

#### 6.2 バックテストページ
- [ ] backtest/page.tsx作成
- [ ] バックテストロジック（モック）
- [ ] simulateBacktest関数の実装
- [ ] メトリクス計算ロジック

#### 6.3 エクスポート機能
- [ ] CSVエクスポート機能
- [ ] チャート画像のダウンロード（将来）

**完了条件**: バックテスト画面が完成し、シミュレーションが動作する

---

### Phase 7: 管理画面実装 - 0.5日

#### 7.1 管理画面コンポーネント
- [ ] UserManagementTable.tsx（ユーザー管理）
- [ ] SystemMetrics.tsx（システムメトリクス）
- [ ] モックユーザーデータの作成

#### 7.2 管理ページ
- [ ] (admin)ルートグループ作成
- [ ] admin/page.tsx作成
- [ ] モック権限チェック

**完了条件**: 管理画面がUIとして完成する

---

### Phase 8: WebSocket統合 - 1日

#### 8.1 WebSocketモック実装
- [ ] useWebSocketフックの作成
- [ ] モックWebSocketサーバー（ローカル）
- [ ] 接続状態の管理
- [ ] リアルタイムデータシミュレーション

#### 8.2 リアルタイム更新の実装
- [ ] 価格更新のシミュレーション
- [ ] ポートフォリオ更新
- [ ] AI判断結果の配信
- [ ] ビジュアルフィードバック（フラッシュ効果）

#### 8.3 タブ同期
- [ ] BroadcastChannelの実装
- [ ] 複数タブでの状態同期

**完了条件**: WebSocketモックが動作し、リアルタイム更新が確認できる

---

### Phase 9: バックエンド統合 - 2-3日

#### 9.1 Supabase認証統合
- [ ] Supabaseプロジェクト設定
- [ ] @supabase/ssrの設定
- [ ] 認証ミドルウェア実装
- [ ] モックから実認証への置き換え

#### 9.2 FastAPI接続
- [ ] APIクライアントの実装
- [ ] モックデータからAPIデータへの置き換え
- [ ] エラーハンドリング
- [ ] ローディング状態の管理

#### 9.3 WebSocket実接続
- [ ] モックWebSocketから実WebSocketへ
- [ ] Redis Pub/Subとの連携
- [ ] リアルタイムデータの取得

**完了条件**: バックエンドとの統合が完了し、実データで動作する

---

### Phase 10: テストと最適化 - 1-2日

#### 10.1 テスト実装
- [ ] コンポーネントテスト
- [ ] 統合テスト
- [ ] E2Eテスト（Playwright）

#### 10.2 パフォーマンス最適化
- [ ] バンドルサイズ最適化
- [ ] dynamic importの実装
- [ ] Core Web Vitalsの測定

#### 10.3 デプロイ準備
- [ ] 環境変数の設定
- [ ] Vercelデプロイ設定
- [ ] CI/CDパイプライン

**完了条件**: 本番環境へのデプロイ準備が完了

---

## 3. バックエンド開発フェーズ (api/) - フロントエンド完成後に開始

### Phase 1: プロジェクト基盤構築 (週1-2)

#### 1.1 環境セットアップ
- [ ] Python 3.12仮想環境作成
- [ ] FastAPI プロジェクト初期化
- [ ] requirements ファイル作成 (base.txt、dev.txt、prod.txt)
- [ ] 依存関係インストール
  - [ ] FastAPI、Uvicorn、Pydantic
  - [ ] SQLAlchemy 2.0、asyncpg
  - [ ] Redis、Celery
  - [ ] structlog、pytest

#### 1.2 基本ディレクトリ構造作成
- [ ] app/ (メインアプリケーション)
- [ ] app/api/v1/ (APIエンドポイント)
- [ ] app/core/ (コア機能)
- [ ] app/models/ (SQLAlchemyモデル)
- [ ] app/schemas/ (Pydanticスキーマ)
- [ ] app/services/ (ビジネスロジック)
- [ ] migrations/ (Alembicマイグレーション)

#### 1.3 設定・依存性注入
- [ ] config.py (環境変数管理)
- [ ] dependencies.py (依存性注入)
- [ ] FastAPIアプリケーション作成 (main.py)
- [ ] CORS設定 (middleware/cors.py)

#### 1.4 データベース基盤
- [ ] Supabase PostgreSQL接続 (core/database.py)
- [ ] SQLAlchemy設定
- [ ] Alembic初期化
- [ ] ベースモデル作成 (models/base.py)

**完了条件**: FastAPIアプリケーションが起動し、データベース接続が確認できる

---

### Phase 2: 認証・ユーザー管理 (週3)

#### 2.1 認証システム
- [ ] Supabase認証ミドルウェア (middleware/auth.py)
- [ ] JWT トークン検証
- [ ] ユーザーモデル (models/user.py)
- [ ] 認証スキーマ (schemas/auth.py)
- [ ] 認証サービス (services/auth_service.py)

#### 2.2 認証API
- [ ] 認証エンドポイント (api/v1/auth.py)
  - [ ] ログイン
  - [ ] トークン更新
  - [ ] ユーザー情報取得
- [ ] 権限管理 (RBAC)
- [ ] セキュリティ機能 (core/security.py)

#### 2.3 認証テスト
- [ ] 認証ミドルウェアテスト
- [ ] 認証APIテスト
- [ ] 権限チェックテスト

**完了条件**: Supabase認証と連携したAPIアクセス制御が動作する

---

### Phase 3: 基本API・データ管理 (週4)

#### 3.1 ポートフォリオ機能
- [ ] ポートフォリオモデル (models/portfolio.py)
- [ ] ポートフォリオスキーマ (schemas/portfolio.py)
- [ ] ポートフォリオサービス (services/portfolio_service.py)
- [ ] ポートフォリオAPI (api/v1/portfolios.py)

#### 3.2 取引機能
- [ ] 取引モデル (models/trade.py)
- [ ] 取引スキーマ (schemas/trade.py)
- [ ] 取引サービス (services/trading_service.py)
- [ ] 取引API (api/v1/trades.py)

#### 3.3 市場データ機能
- [ ] 市場データモデル (models/market_data.py)
- [ ] yfinance API連携 (external/yfinance_api.py)
- [ ] 市場データサービス (services/market_data_service.py)
- [ ] 市場データAPI (api/v1/market.py)

**完了条件**: 基本的なCRUD APIが動作し、フロントエンドとの連携テストが完了する

---

### Phase 4: WebSocket・リアルタイム通信 (週5)

#### 4.1 WebSocket基盤
- [ ] WebSocket接続管理 (core/websocket_manager.py)
- [ ] Redis Pub/Sub設定 (core/redis_client.py)
- [ ] WebSocketミドルウェア
- [ ] 接続認証・権限管理

#### 4.2 リアルタイムデータ配信
- [ ] 価格データ配信サービス (services/websocket_service.py)
- [ ] ポートフォリオ更新配信
- [ ] AI判断結果配信
- [ ] WebSocket API (api/v1/websocket.py)

#### 4.3 メッセージング
- [ ] WebSocketメッセージスキーマ (schemas/websocket.py)
- [ ] イベント定義・ルーティング
- [ ] 購読管理機能

**完了条件**: WebSocketによるリアルタイム通信が安定して動作し、フロントエンドとの連携が確認できる

---

### Phase 5: 外部API連携 (週6)

#### 5.1 証券API連携
- [ ] 立花証券API連携 (external/tachibana_api.py)
- [ ] API認証・トークン管理
- [ ] 注文発注・取消機能
- [ ] 残高・約定照会機能
- [ ] エラーハンドリング・リトライ

#### 5.2 AI Provider API
- [ ] OpenAI API連携 (external/openai_client.py)
- [ ] Gemini API連携 (external/gemini_client.py)
- [ ] ベースAPIクライアント (external/base_client.py)
- [ ] レート制限・コスト管理

#### 5.3 データソース拡張
- [ ] yfinance拡張機能
- [ ] 複数データソース統合
- [ ] データ品質チェック

**完了条件**: 外部API連携が安定して動作し、実際の取引・AI分析が可能になる

---

### Phase 6: LangGraph AI処理システム (週7-8)

#### 6.1 LangGraphエージェント
- [ ] 市場分析エージェント (agents/market_analyzer.py)
- [ ] テクニカル分析エージェント (agents/technical_analyzer.py)
- [ ] チャート生成エージェント (agents/chart_generator.py)
- [ ] 判断決定エージェント (agents/decision_maker.py)

#### 6.2 ワークフロー・チェーン
- [ ] ワークフロー状態定義 (langgraph/state.py)
- [ ] 分析ワークフロー (workflows/analysis_workflow.py)
- [ ] 取引判断チェーン (chains/trading_chain.py)

#### 6.3 AI判断・チャート生成
- [ ] AI判断モデル (models/ai_decision.py)
- [ ] AI判断スキーマ (schemas/ai_decision.py)
- [ ] AIサービス (services/ai_service.py)
- [ ] チャート生成機能 (utils/chart_generator.py)
  - [ ] matplotlib + mplfinance
  - [ ] 画像保存・URL生成
- [ ] AI分析API (api/v1/ai_analysis.py)

**完了条件**: LangGraphによるAI分析システムが動作し、チャート画像生成機能が利用できる

---

### Phase 7: バックテストシステム (週9)

#### 7.1 バックテスト基盤
- [ ] バックテストモデル (models/backtest.py)
- [ ] バックテストスキーマ (schemas/backtest.py)
- [ ] バックテストサービス (services/backtest_service.py)

#### 7.2 Celeryタスクシステム
- [ ] Celery設定 (tasks/celery_app.py)
- [ ] バックテストタスク (tasks/backtest_tasks.py)
- [ ] 進捗管理・通知タスク
- [ ] タスクキュー監視

#### 7.3 バックテスト実行・結果生成
- [ ] 戦略実行エンジン
- [ ] パフォーマンス指標計算
- [ ] 結果チャート生成 (matplotlib)
- [ ] バックテストAPI (api/v1/backtest.py)

**完了条件**: バックテストシステムが動作し、設定から結果生成まで完全なフローが完成する

---

### Phase 8: 管理者機能・監視 (週10)

#### 8.1 管理者API
- [ ] ユーザー管理API (api/v1/admin.py)
- [ ] システムメトリクス取得
- [ ] AI使用量・コスト監視
- [ ] エラーログ管理

#### 8.2 監視・ログシステム
- [ ] 構造化ログ設定 (middleware/logging.py)
- [ ] Prometheus メトリクス
- [ ] パフォーマンス監視
- [ ] アラート機能

#### 8.3 セキュリティ強化
- [ ] レート制限 (middleware/rate_limit.py)
- [ ] APIキー暗号化
- [ ] 監査ログ
- [ ] セキュリティヘッダー

**完了条件**: 管理者機能と監視システムが完成し、本番運用に必要な機能が揃う

---

### Phase 9: テスト・デプロイ準備 (週11)

#### 9.1 テスト実装
- [ ] 単体テスト (pytest)
  - [ ] サービステスト
  - [ ] モデルテスト
  - [ ] ユーティリティテスト
- [ ] 統合テスト
  - [ ] APIテスト
  - [ ] WebSocketテスト
- [ ] E2Eテスト
- [ ] テストカバレッジ80%達成

#### 9.2 Docker化・デプロイ準備
- [ ] Dockerfile作成 (本番・開発用)
- [ ] docker-compose設定
- [ ] 環境変数設定
- [ ] Cloud Run デプロイ設定

#### 9.3 パフォーマンス最適化
- [ ] データベースクエリ最適化
- [ ] キャッシュ戦略調整
- [ ] 非同期処理最適化
- [ ] リソース使用量監視

**完了条件**: 本番デプロイ可能な状態でテストカバレッジ目標達成、パフォーマンス要件満足

---

## 4. 統合・最終フェーズ

### Phase 10: フロント・バック統合テスト (週12)

#### 4.1 統合テスト
- [ ] フロントエンド・バックエンド連携テスト
- [ ] WebSocket通信テスト
- [ ] 認証フロー統合テスト
- [ ] AI分析フロー統合テスト
- [ ] バックテストフロー統合テスト

#### 4.2 本番環境デプロイ
- [ ] Vercel デプロイ (フロントエンド)
- [ ] Cloud Run デプロイ (バックエンド)
- [ ] Supabase本番環境設定
- [ ] Redis本番環境設定
- [ ] ドメイン・SSL設定

#### 4.3 最終調整
- [ ] パフォーマンス最終調整
- [ ] セキュリティ最終確認
- [ ] 運用監視設定
- [ ] ドキュメント整備

**完了条件**: 本番環境で全機能が正常動作し、運用開始可能な状態

---

## 5. 進捗管理ガイドライン（改訂版）

### 5.1 UIファースト開発の進め方
- **Phase 1-8**: UI実装に集中（約7-8日）
- **Phase 9**: バックエンド統合（2-3日）
- **Phase 10**: テストと最適化（1-2日）
- **合計工期**: 約10-13日でフロントエンド完成

### 5.2 フェーズごとのブランチ管理
```bash
# 各フェーズ開始時
git checkout -b feature/phase-X-description

# フェーズ完了時
git checkout develop
git merge feature/phase-X-description
```

### 5.3 チェックリスト運用
- 各フェーズのタスクは必ずチェックリスト形式で管理
- 完了時には動作確認も含めてチェック
- `docs/development_phases_plan.md`を都度更新

### 5.4 品質基準
- **UI段階**: モックデータで全機能が動作確認できる
- **統合段階**: 実データでの動作確認
- **最終段階**: パフォーマンス要件とテストカバレッジ達成

### 5.5 開発のポイント
- サンプル実装（`docs/kaboom-sample.jsx`）を最大限活用
- モックデータでUI完成を優先
- バックエンド統合は最後にまとめて実施
- 早期に動くものを作り、段階的に改善

この改訂版により、UIファーストで効率的に開発を進め、早期に動作確認可能なシステムを構築できます。