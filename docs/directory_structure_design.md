# 株式自動売買管理システム - ディレクトリ構成設計書

## プロジェクト全体構成

```
kaboom/
├── docs/                               # 設計書・ドキュメント
│   ├── web_application_planning.md     # 既存の設計書
│   └── directory_structure_design.md   # 本書（ディレクトリ構成設計）
├── web/                                # フロントエンド (Next.js 15)
├── api/                                # バックエンド (FastAPI)
├── shared/                             # 共通設定・型定義
├── .github/                            # GitHub Actions
├── .gitignore
└── README.md
```

## 1. Webディレクトリ（フロントエンド）詳細設計

### 1.1 技術スタック（Context7で確認済み）

- **Next.js 15**: App Router、RSC対応、最新のReact 19機能サポート
- **React 19**: 新しいフック（useActionState, useOptimistic等）、Server Components
- **TypeScript**: 最新の型システム機能
- **Tailwind CSS**: utility-first CSS、設定簡単、高性能
- **Zustand**: 軽量状態管理、TypeScript完全サポート、ミドルウェア豊富
- **Supabase**: 認証（@supabase/ssr）、データベース操作

### 1.2 詳細ディレクトリ構成

```
web/
├── src/
│   ├── app/                            # Next.js 15 App Router
│   │   ├── (auth)/                     # 認証ルートグループ
│   │   │   ├── login/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   ├── register/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   └── layout.tsx              # 認証レイアウト
│   │   ├── (dashboard)/                # ダッシュボードルートグループ
│   │   │   ├── dashboard/
│   │   │   │   ├── page.tsx            # メインダッシュボード
│   │   │   │   └── loading.tsx
│   │   │   ├── portfolio/
│   │   │   │   ├── page.tsx            # ポートフォリオ画面
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx        # 個別ポートフォリオ
│   │   │   ├── ai-analysis/
│   │   │   │   ├── page.tsx            # AI分析画面
│   │   │   │   └── [symbol]/
│   │   │   │       └── page.tsx        # 銘柄別分析
│   │   │   ├── backtest/
│   │   │   │   ├── page.tsx            # バックテスト画面
│   │   │   │   └── results/
│   │   │   │       └── [id]/
│   │   │   │           └── page.tsx    # バックテスト結果
│   │   │   ├── settings/
│   │   │   │   ├── page.tsx            # 設定画面
│   │   │   │   ├── profile/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── api-keys/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── notifications/
│   │   │   │       └── page.tsx
│   │   │   └── layout.tsx              # ダッシュボードレイアウト
│   │   ├── (admin)/                    # 管理者ルートグループ
│   │   │   ├── admin/
│   │   │   │   ├── page.tsx            # 管理者ダッシュボード
│   │   │   │   ├── users/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   └── [id]/
│   │   │   │   │       └── page.tsx
│   │   │   │   ├── metrics/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── ai-settings/
│   │   │   │       └── page.tsx
│   │   │   └── layout.tsx              # 管理者レイアウト
│   │   ├── api/                        # Next.js API Routes（必要時）
│   │   │   └── auth/
│   │   │       └── callback/
│   │   │           └── route.ts        # Supabase認証コールバック
│   │   ├── layout.tsx                  # ルートレイアウト（HTML、body）
│   │   ├── page.tsx                    # ランディングページ
│   │   ├── globals.css                 # Tailwind CSS import
│   │   ├── loading.tsx                 # グローバルローディング
│   │   ├── error.tsx                   # グローバルエラーハンドリング
│   │   └── not-found.tsx               # 404ページ
│   ├── components/
│   │   ├── ui/                         # 基本UIコンポーネント
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Toast.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── DataTable.tsx
│   │   │   └── index.ts                # re-export
│   │   ├── charts/                     # チャート関連（Recharts）
│   │   │   ├── PortfolioChart.tsx      # 資産推移チャート
│   │   │   ├── PriceChart.tsx          # 価格チャート
│   │   │   ├── PerformanceChart.tsx    # パフォーマンス分析
│   │   │   ├── BacktestChart.tsx       # バックテスト結果表示
│   │   │   └── ChartContainer.tsx      # チャート共通ラッパー
│   │   ├── dashboard/                  # ダッシュボード専用
│   │   │   ├── Header.tsx              # ヘッダー（ナビ、通知、ユーザー）
│   │   │   ├── Sidebar.tsx             # サイドバーナビゲーション
│   │   │   ├── PortfolioSummary.tsx    # ポートフォリオサマリーカード
│   │   │   ├── RealtimeTable.tsx       # リアルタイムAI判断テーブル
│   │   │   └── WebSocketIndicator.tsx  # 接続状態表示
│   │   ├── trading/                    # 取引関連
│   │   │   ├── TradeForm.tsx           # 取引フォーム
│   │   │   ├── OrderHistory.tsx        # 注文履歴
│   │   │   ├── PositionList.tsx        # ポジション一覧
│   │   │   ├── AIDecisionPanel.tsx     # AI判断結果表示
│   │   │   └── TechnicalIndicators.tsx # テクニカル指標ダッシュボード
│   │   ├── backtest/                   # バックテスト関連
│   │   │   ├── BacktestForm.tsx        # バックテスト設定フォーム
│   │   │   ├── ResultsSummary.tsx      # 結果サマリー表示
│   │   │   ├── ProgressBar.tsx         # 実行進捗表示
│   │   │   ├── TradeHistoryTable.tsx   # 取引履歴テーブル
│   │   │   └── ParameterPresets.tsx    # プリセット管理
│   │   ├── auth/                       # 認証関連
│   │   │   ├── LoginForm.tsx
│   │   │   ├── RegisterForm.tsx
│   │   │   ├── PasswordResetForm.tsx
│   │   │   └── AuthProvider.tsx        # 認証状態プロバイダー
│   │   └── shared/                     # 共通コンポーネント
│   │       ├── Loading.tsx             # ローディング表示
│   │       ├── ErrorBoundary.tsx       # エラーバウンダリ
│   │       ├── ClientOnly.tsx          # クライアント専用レンダリング
│   │       └── Providers.tsx           # アプリケーションプロバイダー
│   ├── hooks/                          # カスタムフック
│   │   ├── useWebSocket.ts             # WebSocket接続管理
│   │   ├── useRealtimePrice.ts         # リアルタイム価格データ
│   │   ├── useAuth.ts                  # 認証状態管理
│   │   ├── useAPI.ts                   # API呼び出し
│   │   ├── useBacktest.ts              # バックテスト操作
│   │   ├── usePortfolio.ts             # ポートフォリオ操作
│   │   ├── useLocalStorage.ts          # ローカルストレージ
│   │   └── useDebounce.ts              # デバウンス処理
│   ├── lib/                            # ユーティリティライブラリ
│   │   ├── supabase/
│   │   │   ├── client.ts               # クライアントサイド用
│   │   │   ├── server.ts               # サーバーサイド用
│   │   │   ├── middleware.ts           # ミドルウェア用
│   │   │   └── types.ts                # Supabase型定義
│   │   ├── api/
│   │   │   ├── client.ts               # APIクライアント
│   │   │   ├── endpoints.ts            # エンドポイント定数
│   │   │   ├── types.ts                # APIレスポンス型
│   │   │   └── error-handler.ts        # エラーハンドリング
│   │   ├── websocket/
│   │   │   ├── manager.ts              # WebSocket接続管理
│   │   │   ├── events.ts               # イベント定義
│   │   │   └── reconnect.ts            # 再接続ロジック
│   │   └── utils/
│   │       ├── formatters.ts           # データフォーマット関数
│   │       ├── validators.ts           # バリデーション関数
│   │       ├── constants.ts            # アプリケーション定数
│   │       ├── date-utils.ts           # 日付操作
│   │       └── chart-utils.ts          # チャート関連ユーティリティ
│   ├── stores/                         # Zustand状態管理
│   │   ├── authStore.ts                # 認証状態
│   │   ├── portfolioStore.ts           # ポートフォリオ状態
│   │   ├── websocketStore.ts           # WebSocket接続状態
│   │   ├── backtestStore.ts            # バックテスト状態
│   │   ├── settingsStore.ts            # アプリケーション設定
│   │   └── notificationStore.ts        # 通知状態
│   ├── types/                          # TypeScript型定義
│   │   ├── api.ts                      # API関連型
│   │   ├── trading.ts                  # 取引関連型
│   │   ├── portfolio.ts                # ポートフォリオ型
│   │   ├── websocket.ts                # WebSocket型
│   │   ├── auth.ts                     # 認証型
│   │   ├── backtest.ts                 # バックテスト型
│   │   └── chart.ts                    # チャート型
│   └── config/                         # 設定
│       ├── constants.ts                # アプリケーション定数
│       ├── environment.ts              # 環境変数
│       └── routes.ts                   # ルート定数
├── public/                             # 静的ファイル
│   ├── logo.svg
│   ├── favicon.ico
│   ├── icons/                          # アイコンファイル
│   └── images/                         # 画像ファイル
├── tests/                              # テスト
│   ├── __mocks__/                      # モック
│   ├── components/                     # コンポーネントテスト
│   ├── hooks/                          # フックテスト
│   ├── pages/                          # ページテスト
│   ├── e2e/                           # E2Eテスト（Playwright）
│   └── utils/                          # テストユーティリティ
├── .env.local                          # 環境変数（ローカル）
├── .env.example                        # 環境変数サンプル
├── next.config.js                      # Next.js設定
├── tailwind.config.ts                  # Tailwind CSS設定
├── tsconfig.json                       # TypeScript設定
├── package.json
├── playwright.config.ts                # E2Eテスト設定
└── README.md
```

### 1.3 主要ライブラリ設定

#### package.json dependencies（推奨バージョン）
```json
{
  "dependencies": {
    "next": "^15.1.8",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@supabase/supabase-js": "^2.45.0",
    "@supabase/ssr": "^0.5.0",
    "zustand": "^5.0.0",
    "recharts": "^2.12.0",
    "react-hook-form": "^7.53.0",
    "@hookform/resolvers": "^3.9.0",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "typescript": "^5.6.0",
    "tailwindcss": "^3.4.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "playwright": "^1.48.0",
    "@playwright/test": "^1.48.0"
  }
}
```

## 2. APIディレクトリ（バックエンド）詳細設計

### 2.1 技術スタック（Context7で確認済み）

- **FastAPI**: 高速、自動ドキュメント生成、WebSocket対応
- **Python 3.12**: 最新の型システム、パフォーマンス改善
- **Supabase PostgreSQL**: スケーラブルなデータベース
- **WebSocket**: ネイティブサポート、リアルタイム通信
- **SQLAlchemy 2.0**: 非同期ORM、型安全
- **Pydantic**: データバリデーション、シリアライゼーション

### 2.2 詳細ディレクトリ構成

```
api/
├── app/
│   ├── __init__.py
│   ├── main.py                         # FastAPIアプリケーション
│   ├── config.py                       # 設定管理（環境変数）
│   ├── dependencies.py                 # 共通依存性注入
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py                     # Supabase認証ミドルウェア
│   │   ├── cors.py                     # CORS設定
│   │   ├── logging.py                  # 構造化ログ
│   │   ├── rate_limit.py               # レート制限
│   │   └── error_handler.py            # エラーハンドリング
│   ├── api/                            # APIエンドポイント
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py               # メインルーター
│   │       ├── auth.py                 # 認証エンドポイント（オプション）
│   │       ├── portfolios.py           # ポートフォリオAPI
│   │       ├── trades.py               # 取引API
│   │       ├── ai_analysis.py          # AI分析API
│   │       ├── backtest.py             # バックテストAPI
│   │       ├── market.py               # 市場データAPI
│   │       ├── websocket.py            # WebSocket API
│   │       ├── admin.py                # 管理者API
│   │       └── charts.py               # チャート画像生成API
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py                 # セキュリティ関連
│   │   ├── database.py                 # データベース接続（Supabase）
│   │   ├── redis_client.py             # Redis接続（キャッシュ）
│   │   ├── exceptions.py               # カスタム例外
│   │   └── websocket_manager.py        # WebSocket接続管理
│   ├── models/                         # SQLAlchemyモデル
│   │   ├── __init__.py
│   │   ├── base.py                     # ベースモデル
│   │   ├── user.py                     # ユーザーモデル
│   │   ├── portfolio.py                # ポートフォリオモデル
│   │   ├── trade.py                    # 取引モデル
│   │   ├── ai_decision.py              # AI判断モデル
│   │   ├── backtest.py                 # バックテストモデル
│   │   └── market_data.py              # 市場データモデル
│   ├── schemas/                        # Pydanticスキーマ
│   │   ├── __init__.py
│   │   ├── base.py                     # ベーススキーマ
│   │   ├── auth.py                     # 認証スキーマ
│   │   ├── portfolio.py                # ポートフォリオスキーマ
│   │   ├── trade.py                    # 取引スキーマ
│   │   ├── ai_decision.py              # AI判断スキーマ
│   │   ├── backtest.py                 # バックテストスキーマ
│   │   ├── websocket.py                # WebSocketメッセージスキーマ
│   │   └── chart.py                    # チャート関連スキーマ
│   ├── services/                       # ビジネスロジック
│   │   ├── __init__.py
│   │   ├── auth_service.py             # 認証サービス
│   │   ├── portfolio_service.py        # ポートフォリオサービス
│   │   ├── trading_service.py          # 取引実行サービス
│   │   ├── market_data_service.py      # 市場データサービス
│   │   ├── ai_service.py               # AI処理サービス
│   │   ├── backtest_service.py         # バックテストサービス
│   │   ├── notification_service.py     # 通知サービス
│   │   └── websocket_service.py        # WebSocket配信サービス
│   ├── external/                       # 外部API連携
│   │   ├── __init__.py
│   │   ├── tachibana_api.py            # 立花証券API
│   │   ├── yfinance_api.py             # yfinance API
│   │   ├── openai_client.py            # OpenAI API
│   │   ├── gemini_client.py            # Gemini API
│   │   └── base_client.py              # 外部APIベースクライアント
│   ├── langgraph/                      # LangGraph AI処理
│   │   ├── __init__.py
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── market_analyzer.py      # 市場分析エージェント
│   │   │   ├── technical_analyzer.py   # テクニカル分析エージェント
│   │   │   ├── chart_generator.py      # チャート生成エージェント
│   │   │   └── decision_maker.py       # 判断決定エージェント
│   │   ├── chains/
│   │   │   ├── __init__.py
│   │   │   └── trading_chain.py        # 取引判断チェーン
│   │   ├── workflows/
│   │   │   ├── __init__.py
│   │   │   └── analysis_workflow.py    # 分析ワークフロー
│   │   └── state.py                    # ワークフロー状態定義
│   ├── tasks/                          # Celeryタスク
│   │   ├── __init__.py
│   │   ├── celery_app.py               # Celery設定
│   │   ├── market_tasks.py             # 市場データ更新タスク
│   │   ├── analysis_tasks.py           # AI分析タスク
│   │   ├── notification_tasks.py       # 通知タスク
│   │   └── backtest_tasks.py           # バックテスト実行タスク
│   └── utils/                          # ユーティリティ
│       ├── __init__.py
│       ├── chart_generator.py          # matplotlib/mplfinanceチャート生成
│       ├── indicators.py               # テクニカル指標計算
│       ├── validators.py               # バリデーション関数
│       ├── formatters.py               # データフォーマット
│       ├── logger.py                   # ログ設定
│       └── cache.py                    # キャッシュユーティリティ
├── migrations/                         # データベースマイグレーション
│   ├── alembic.ini                     # Alembic設定
│   ├── env.py                          # マイグレーション環境
│   └── versions/                       # マイグレーションファイル
├── tests/                              # テスト
│   ├── __init__.py
│   ├── conftest.py                     # pytest設定
│   ├── unit/                           # 単体テスト
│   │   ├── test_services/
│   │   ├── test_models/
│   │   └── test_utils/
│   ├── integration/                    # 統合テスト
│   │   ├── test_api/
│   │   └── test_websocket/
│   └── e2e/                           # E2Eテスト
│       └── test_trading_flow.py
├── scripts/                           # スクリプト
│   ├── init_db.py                     # データベース初期化
│   ├── seed_data.py                   # テストデータ投入
│   └── start_services.py              # サービス開始
├── docker/
│   ├── Dockerfile                     # 本番用Docker
│   ├── Dockerfile.dev                 # 開発用Docker
│   ├── docker-compose.yml             # 開発環境
│   └── docker-compose.prod.yml        # 本番環境
├── requirements/
│   ├── base.txt                       # 基本パッケージ
│   ├── dev.txt                        # 開発用パッケージ
│   └── prod.txt                       # 本番用パッケージ
├── .env.example                       # 環境変数サンプル
├── pyproject.toml                     # Python設定
└── README.md
```

### 2.3 主要ライブラリ設定

#### requirements/base.txt（推奨バージョン）
```txt
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.12
pydantic==2.10.0
pydantic-settings==2.6.0
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
redis==5.2.0
celery==5.4.0
structlog==24.4.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
aiohttp==3.11.10
websockets==14.1
matplotlib==3.10.0
mplfinance==0.12.10b0
pandas==2.2.3
numpy==2.2.0
```

## 3. 共通設定・型定義（shared）

### 3.1 ディレクトリ構成

```
shared/
├── types/                             # 共通TypeScript型定義
│   ├── api.ts                         # APIレスポンス共通型
│   ├── websocket.ts                   # WebSocketメッセージ型
│   ├── trading.ts                     # 取引関連型
│   └── common.ts                      # 汎用型定義
├── constants/
│   ├── endpoints.ts                   # API エンドポイント定数
│   ├── websocket-events.ts            # WebSocketイベント定数
│   └── trading-constants.ts           # 取引関連定数
├── schemas/                           # バリデーション用スキーマ
│   ├── api-schemas.ts                 # API用Zodスキーマ
│   └── form-schemas.ts                # フォーム用スキーマ
└── utils/
    ├── date-format.ts                 # 日付フォーマット共通関数
    └── currency-format.ts             # 通貨フォーマット関数
```

## 4. CI/CDパイプライン（.github）

### 4.1 ワークフロー構成

```
.github/
└── workflows/
    ├── web-test.yml                   # フロントエンドテスト
    ├── api-test.yml                   # バックエンドテスト
    ├── web-deploy.yml                 # Vercelデプロイ
    ├── api-deploy.yml                 # Cloud Runデプロイ
    ├── type-check.yml                 # TypeScript型チェック
    └── security-check.yml             # セキュリティスキャン
```

## 5. 開発環境セットアップ手順

### 5.1 フロントエンド（web）

```bash
cd web
npm install
cp .env.example .env.local
# .env.localを編集してSupabase設定を追加
npm run dev
```

### 5.2 バックエンド（api）

```bash
cd api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements/dev.txt
cp .env.example .env
# .envを編集してデータベース・外部API設定を追加
python scripts/init_db.py
uvicorn app.main:app --reload
```

## 6. 開発ガイドライン

### 6.1 ファイル命名規則

- **コンポーネント**: PascalCase (例: `UserProfile.tsx`)
- **フック**: camelCase with use prefix (例: `useWebSocket.ts`)
- **ユーティリティ**: kebab-case (例: `date-utils.ts`)
- **API ルート**: snake_case (例: `portfolio_service.py`)

### 6.2 インポート順序

1. React/Next.js関連
2. 外部ライブラリ
3. 内部ライブラリ（@/から始まる）
4. 相対パスインポート

### 6.3 型定義ガイドライン

- **共通型**: `shared/types/` に配置
- **コンポーネント固有型**: コンポーネント同一ファイル内で定義
- **API関連型**: フロントは `types/api.ts`、バックエンドは `schemas/`

### 6.4 状態管理ベストプラクティス

- **Zustand**: 軽量で高性能、TypeScript完全サポート
- **ストア分割**: 機能ごとに独立したストア作成
- **ミドルウェア**: persist（永続化）、devtools（開発ツール）積極活用

## 7. パフォーマンス最適化

### 7.1 フロントエンド最適化

- **Next.js 15機能**: Server Components、Dynamic Imports積極活用
- **Recharts**: チャート使用ページのみdynamic import
- **画像最適化**: Next.js Image コンポーネント使用
- **バンドル分析**: `@next/bundle-analyzer` 導入

### 7.2 バックエンド最適化

- **FastAPI**: 非同期処理、自動ドキュメント生成活用
- **WebSocket**: 効率的な接続管理、メッセージ配信
- **キャッシュ**: Redis使用、適切なTTL設定
- **データベース**: コネクションプール、インデックス最適化

この設計書をもとに、モノレポ構成での効率的な開発が可能になります。各ライブラリの最新機能を活用し、保守性とパフォーマンスを両立したアーキテクチャです。