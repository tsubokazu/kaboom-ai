# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a stock trading management system with AI-powered analysis and backtesting capabilities. The project follows a monorepo structure with separate frontend and backend applications:

- **Frontend**: Next.js 15 + React 19 (`web/` directory) - Trading dashboard, portfolio management, AI analysis UI
- **Backend**: FastAPI + Python 3.12 (`api/` directory) - Trading API, AI processing with LangGraph, WebSocket services
- **Shared**: Common types and configurations (`shared/` directory)

## Architecture

### Frontend Architecture (web/)
- **Framework**: Next.js 15 with App Router and React Server Components
- **Authentication**: Supabase Auth with SSR cookies (@supabase/ssr)
- **State Management**: Zustand for client state, Server Components + fetch cache for server data, WebSocket for real-time updates
- **Real-time**: Native WebSocket connections with automatic reconnection
- **Charts**: Recharts for interactive charts (dynamic import), backend-generated images for AI/backtest results
- **Routing**: Route groups for logical separation: (auth), (dashboard), (admin)

### Backend Architecture (api/)
- **Framework**: FastAPI with async/await throughout
- **AI Processing**: OpenRouter統一API経由で複数AIモデル（GPT-4, Claude, Gemini等）を統合管理
- **Real-time**: WebSocket + Redis Pub/Sub for real-time data distribution
- **External APIs**: Integration with trading APIs (立花証券), market data (yfinance)
- **Background Tasks**: Celery for heavy processing (backtests, AI analysis, market data updates)
- **Charts**: matplotlib + mplfinance for generating chart images served to frontend

### Data Flow
1. **Authentication**: Supabase handles auth, backend validates JWT tokens
2. **Real-time Data**: Market data flows through WebSocket connections managed by Redis Pub/Sub
3. **AI Analysis**: OpenRouter統一APIで複数AIモデル（GPT-4, Claude, Gemini）による並列分析・合意形成
4. **Trading**: Frontend sends trade requests to FastAPI, which executes via external trading APIs

## Development Commands

The backend API implementation is complete (Phase 2C). Here are the development commands:

### Frontend (web/)
```bash
# Development
cd web && npm run dev

# Build and type checking
cd web && npm run build
cd web && npm run type-check

# Testing
cd web && npm run test
cd web && npm run test:e2e  # Playwright tests

# Linting
cd web && npm run lint
cd web && npm run lint:fix
```

### Backend (api/)
```bash
# Development
cd api && uvicorn app.main:app --reload

# Testing
cd api && pytest
cd api && pytest tests/unit/
cd api && pytest tests/integration/

# Type checking and linting
cd api && mypy .
cd api && black .
cd api && isort .

# Database migrations
cd api && alembic upgrade head
cd api && alembic revision --autogenerate -m "description"

# Background services
cd api && celery -A app.tasks.celery_app worker --loglevel=info
cd api && celery -A app.tasks.celery_app beat --loglevel=info
```

## Key Implementation Notes

### Authentication Integration
- Frontend uses @supabase/ssr for cookie-based session management
- Backend validates Supabase JWT tokens for API access
- WebSocket connections authenticate via query parameters or initial message

### WebSocket Architecture
- Connection manager handles multiple concurrent connections
- Redis Pub/Sub enables horizontal scaling of WebSocket servers
- Automatic reconnection with exponential backoff on frontend
- Tab synchronization using BroadcastChannel to prevent duplicate connections

### AI Processing Pipeline (OpenRouter統合戦略)
- **統一API**: OpenRouter (https://openrouter.ai/) 経由で20+のAIモデルにアクセス
- **モデル設定**:
  - Technical Analysis: `openai/gpt-4-turbo-preview`
  - Sentiment Analysis: `anthropic/claude-3-sonnet` 
  - Risk Assessment: `google/gemini-pro-vision`
  - Fallback: `meta-llama/llama-2-70b-chat`
- **コスト管理**: 統一ダッシュボードでリアルタイム使用量・コスト監視
- **Chart generation**: matplotlib/mplfinance でサーバーサイド画像生成
- **AI decisions**: Redis経由でキャッシュ・WebSocket配信
- **フォールバック**: モデル障害時の自動切り替え機能

### Data Fetching Strategy
Instead of TanStack Query, use Next.js 15 native features combined with WebSocket for optimal performance:

**Server Components (for initial data):**
```typescript
// Server Component with automatic caching
async function PortfolioPage() {
  const portfolio = await fetch(`${process.env.API_URL}/api/v1/portfolios`, {
    headers: { Authorization: `Bearer ${token}` },
    next: { revalidate: 60 } // Cache for 1 minute
  })
  return <PortfolioView initialData={portfolio} />
}

// Static data with longer cache
async function MarketDataPage() {
  const indicators = await fetch('/api/v1/market/indicators', {
    next: { revalidate: 300 } // Cache for 5 minutes
  })
  return <TechnicalIndicators data={indicators} />
}
```

**Client Components (for real-time updates):**
```typescript
// WebSocket hook for real-time updates
function useRealtimePortfolio(initialData: Portfolio) {
  const { socket } = useWebSocket()
  const [portfolio, setPortfolio] = useState(initialData)
  
  useEffect(() => {
    if (!socket) return
    
    socket.on('portfolio_update', (data: Portfolio) => {
      setPortfolio(data)
    })
    
    return () => socket.off('portfolio_update')
  }, [socket])
  
  return portfolio
}

// Price updates with optimistic UI
function useRealtimePrice(symbol: string) {
  const { socket } = useWebSocket()
  const [price, setPrice] = useState<PriceData | null>(null)
  
  useEffect(() => {
    socket?.on(`price_update:${symbol}`, setPrice)
    return () => socket?.off(`price_update:${symbol}`)
  }, [socket, symbol])
  
  return price
}
```

**Data Mutations (with optimistic updates):**
```typescript
// Trading with optimistic UI using React 19 useOptimistic
function useTradeExecution() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [optimisticTrades, addOptimisticTrade] = useOptimistic(
    trades,
    (state, newTrade: Trade) => [...state, newTrade]
  )
  
  const executeTrade = async (tradeData: TradeRequest) => {
    // Optimistic update
    addOptimisticTrade({ ...tradeData, status: 'pending', id: generateId() })
    
    try {
      const result = await fetch('/api/v1/trades', {
        method: 'POST',
        body: JSON.stringify(tradeData)
      })
      // Real data will come via WebSocket
    } catch (error) {
      // Handle error, remove optimistic update
    }
  }
  
  return { trades: optimisticTrades, executeTrade }
}
```

### Performance Considerations
- Frontend: Dynamic imports for charts, Server Components for data fetching, Next.js automatic caching
- Backend: Async everywhere, Redis caching for market data, database connection pooling
- Real-time: Efficient WebSocket message batching and compression
- Data Strategy: Server Components + fetch cache instead of TanStack Query for better RSC integration

### Development Phases (UIファースト戦略)
The project follows a UI-first development approach (see `docs/development_phases_plan.md`):
- **Phase 1-8**: UI implementation with mock data (7-8 days)
- **Phase 9**: Backend integration (2-3 days)
- **Phase 10**: Testing and optimization (1-2 days)
- **Key Resource**: `docs/kaboom-sample.jsx` - Sample implementation to be migrated
- Each phase creates a feature branch and updates the plan document upon completion

## Git Workflow & Development Best Practices

### Branch Strategy (UIファースト開発)
- **main**: Production-ready code only
- **develop**: Integration branch for features
- **feature/phase-X-*****: Phase-based development branches
  - `feature/phase-1-project-setup`
  - `feature/phase-2-design-system`
  - `feature/phase-3-auth-ui`
  - `feature/phase-4-dashboard`
  - `feature/phase-5-ai-analysis`
  - `feature/phase-6-backtest`
  - `feature/phase-7-admin`
  - `feature/phase-8-websocket`
  - `feature/phase-9-backend-integration`
  - `feature/phase-10-testing`
- **hotfix/***: Emergency fixes for production issues

### Pre-Commit Requirements
Always ensure the following passes before committing:

**Frontend (web/):**
```bash
cd web
# 1. Format code with Prettier
npx prettier --write .

# 2. Run linting checks
npm run lint        # ESLint checks must pass

# 3. Type checking
npx tsc --noEmit    # TypeScript compilation must succeed

# 4. Run tests (when available)
npm run test        # All unit tests must pass

# 5. Build verification (optional for commit, required for deploy)
npm run build       # Production build must succeed
```

**Backend (api/):**
```bash
cd api
# 1. Format code
black .             # Auto-format Python code
isort .             # Sort imports

# 2. Check formatting and linting
black --check .     # Code formatting must be correct
isort --check-only . # Import sorting must be correct
mypy .              # Type checking must pass

# 3. Run tests
pytest              # All tests must pass
```

### Commit Process
1. **Stop development server** if running in background
2. **Run all pre-commit checks** as listed above
3. **Stage changes**: `git add .`
4. **Create commit** with proper message format
5. **Switch to develop** and merge feature branch
6. **Create new feature branch** for next phase

### Commit Message Format
Follow conventional commits:
- `feat: add WebSocket connection management`
- `fix: resolve authentication token refresh issue`
- `docs: update API documentation`
- `refactor: extract chart generation logic`
- `test: add integration tests for portfolio API`
- `chore: update dependencies`

### Code Quality Standards
- **Frontend**: 80%+ test coverage, all TypeScript strict mode rules
- **Backend**: 80%+ test coverage, type hints required for all functions
- **Security**: No API keys or secrets in code, all user inputs validated
- **Performance**: Core Web Vitals targets met, API responses under 1s

### Pre-Commit Checklist
- [ ] All linting and type checking passes
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] No console.log or print statements left in code
- [ ] Environment variables used for configuration
- [ ] Code follows existing patterns and architecture
- [ ] Documentation updated if APIs changed

### CI/CD Integration (Future)
The project will use GitHub Actions to enforce these standards:
- Automated linting and type checking on PRs
- Test suite must pass before merge
- Build verification for both frontend and backend
- Security scanning for dependencies

## OpenRouter統合実装ガイド

### 環境変数設定
```bash
# 必須設定
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx

# オプション設定
OPENROUTER_DEBUG=false
OPENROUTER_LOG_REQUESTS=true
OPENROUTER_COST_TRACKING=true
```

### AIモデル設定例
```python
AI_MODEL_CONFIG = {
    "technical_analysis": {
        "primary": "openai/gpt-4-turbo-preview",
        "fallback": "anthropic/claude-3-sonnet",
        "temperature": 0.1,
        "max_tokens": 1000
    },
    "sentiment_analysis": {
        "primary": "anthropic/claude-3-sonnet", 
        "fallback": "openai/gpt-4-turbo-preview",
        "temperature": 0.2,
        "max_tokens": 800
    }
}
```

### API呼び出し例
```python
# 基本的なAI分析リクエスト
async def analyze_stock(symbol: str, analysis_type: str):
    payload = {
        "model": "openai/gpt-4-turbo-preview",
        "messages": [
            {"role": "system", "content": TECHNICAL_ANALYSIS_PROMPT},
            {"role": "user", "content": f"銘柄{symbol}のテクニカル分析を実行"}
        ],
        "temperature": 0.1,
        "max_tokens": 1000
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json=payload
        ) as response:
            return await response.json()
```

### エラーハンドリング
- `429 Rate Limit`: 指数バックオフでリトライ
- `503 Service Unavailable`: フォールバックモデルに切り替え
- `400 Bad Request`: プロンプト形式エラー - 構造化レスポンスの確認

## 標準ドキュメント体系

### API設計文書
- **設計計画**: `docs/api-development-plan.md` - OpenRouter統合を軸とした4週間実装計画
- **ADR**: `docs/architecture/adr/0001-openrouter-ai-integration.md` - OpenRouter採用の技術的根拠
- **エラーカタログ**: `docs/api/error-catalog.md` - RFC 7807準拠の統一エラー定義
- **OpenRouter統合**: `docs/ai/openrouter-integration.md` - 実装レベルの詳細設計
- **API仕様**: `docs/api/openapi.yaml` - 完全なREST API契約

### 実装優先度
1. **Week 1**: OpenRouterクライアント基盤 + 基本API契約
2. **Week 2**: AI分析ジョブ（非同期処理） + バックテスト機能
3. **Week 3**: 認証システム + セキュリティ + 監視
4. **Week 4**: パフォーマンス最適化 + E2Eテスト

## Important File Locations

- **API設計**: `docs/api-development-plan.md` - OpenRouter統合API開発計画
- **設計根拠**: `docs/architecture/adr/` - 重要な技術選択の意思決定記録
- **Frontend Planning**: `docs/web_application_planning.md` - 詳細なUI仕様
- **Backend Planning**: Second half of `docs/web_application_planning.md` - API システム設計
- **Architecture**: `docs/directory_structure_design.md` - ディレクトリ構造設計

### 新規実装時の参照順序
1. `docs/api-development-plan.md` - 全体計画の確認
2. `docs/architecture/adr/0001-openrouter-ai-integration.md` - 技術選択の理解  
3. `docs/api/openapi.yaml` - API契約の詳細確認
4. `docs/ai/openrouter-integration.md` - 実装コード例の参照

When implementing, prioritize OpenRouter integration and follow the 4-week development schedule outlined in the API development plan. Always refer to the ADR for technical decision rationale and the comprehensive error catalog for consistent error handling.

## 🎯 Phase 2C 実装完了状況 (2025-09-12)

### ✅ Phase 2A完了済み実装 (2025-09-09)
**OpenRouter AI統合基盤:**
- ✅ `app/services/openrouter_client.py` - 完全なAIクライアント実装
- ✅ GPT-4, Claude, Gemini等マルチモデル対応
- ✅ フォールバック機能（モデル障害時自動切り替え）
- ✅ コスト計算・使用量追跡機能

**認証・セキュリティ基盤:**
- ✅ `app/middleware/auth.py` - JWT認証・RBAC実装
- ✅ `app/middleware/rate_limit.py` - 役割別レート制限
- ✅ `app/middleware/security.py` - XSS/CSRF保護
- ✅ Supabase認証統合完了・接続確認済み

### ✅ Phase 2A完了実装 (2025-09-09)

#### 1. Redis統合基盤 (`app/services/redis_client.py`)
- ✅ セッション管理（JWT token + user data）
- ✅ データキャッシング（価格情報・分析結果）
- ✅ Pub/Sub配信（WebSocket real-time updates）
- ✅ ヘルスチェック・接続状態監視
- ✅ Redis接続確認済み（localhost:6379）

#### 2. WebSocket接続管理システム (`app/websocket/`)
- ✅ Redis Pub/Sub統合によるクラスター対応
- ✅ リアルタイム価格配信機能
- ✅ ポートフォリオ更新・AI分析完了通知
- ✅ 接続管理・ハートビート・統計情報

#### 3. Celery統合とタスクワーカー (`app/tasks/`)
- ✅ **AI分析タスク** (`ai_analysis_tasks.py`): 
  - 複数モデル並列分析・合意形成
  - テクニカル・センチメント・リスク分析
  - 進行状況リアルタイム通知
- ✅ **バックテストタスク** (`backtest_tasks.py`):
  - 戦略検証・ポートフォリオ最適化
  - モンテカルロシミュレーション
  - パフォーマンス指標計算
- ✅ **市場データタスク** (`market_data_tasks.py`):
  - 定期株価更新・システムメトリクス収集
  - 価格アラート監視・市場営業時間判定
- ✅ **通知タスク** (`notification_tasks.py`):
  - WebSocket・メール・バッチ通知処理
  - 通知履歴管理・日次サマリー

#### 4. データAPI実装 (`app/routers/`)
- ✅ **ポートフォリオAPI** (`portfolios.py`):
  - CRUD操作・AI分析・最適化
  - パフォーマンス分析・リスク指標
- ✅ **取引API** (`trades.py`):
  - 売買注文・履歴管理・統計分析
  - リアルタイム市場データ・価格アラート

#### 5. API統合・ヘルスチェック
- ✅ 全36エンドポイント稼働確認
- ✅ Redis接続状況監視機能追加
- ✅ Celery 16タスク登録・動作確認
- ✅ WebSocket統合テスト成功

### ✅ Phase 2B新規完了実装 (2025-09-10)

#### 1. SQLAlchemyモデル定義・データベース統合
- ✅ **User, Portfolio, Holding, Order, Trade**（5モデル完全実装）
- ✅ **PostgreSQL直接接続**（Supabase統合・非同期SQLAlchemy）
- ✅ **Alembicマイグレーション**（5テーブル作成・制約設定完了）
- ✅ **データベース接続管理**（接続プール・ライフサイクル・ヘルスチェック）

#### 2. ポートフォリオAPI実装（実データベース対応）
- ✅ **PortfolioService**（CRUD・メトリクス計算・キャッシュ統合）
- ✅ **9エンドポイント**（作成・更新・削除・銘柄追加・分析・最適化）
- ✅ **リアルタイム評価額・損益計算**
- ✅ **AI分析・最適化タスク統合**

#### 3. 取引API実装（実データベース対応）
- ✅ **TradingService**（注文・約定・統計管理）
- ✅ **11エンドポイント**（注文CRUD・履歴・統計・アラート・手動約定）
- ✅ **注文ライフサイクル管理**（作成→約定→決済）
- ✅ **ポートフォリオ連携・実現損益計算**

#### 4. yfinance市場データ強化・リアルタイム価格更新
- ✅ **MarketDataService**（リアルタイム価格・テクニカル指標・企業情報）
- ✅ **テクニカル指標計算**（SMA・RSI・MACD・ボリンジャーバンド）
- ✅ **日本株10銘柄対応**・バッチ処理最適化
- ✅ **Celeryタスク統合**（単一・一括・テクニカル指標更新）

### ✅ Phase 2C完了実装 (2025-09-12)

#### 1. 高度AI分析システム強化
- ✅ **マルチモデル合意システム** (`app/services/advanced_ai_service.py`)
- ✅ **GPT-4/Claude/Gemini並列分析・合意形成** (4つの合意戦略実装)
- ✅ **カスタム分析・プレミアム機能** (カスタムプロンプト・重み調整)
- ✅ **パフォーマンス追跡・コスト最適化** (モデル精度・自動最適化)

#### 2. 管理ダッシュボード・監視システム
- ✅ **リアルタイムシステム監視** (`app/services/monitoring_service.py`)
- ✅ **自動アラート・通知システム** (閾値監視・WebSocket配信)
- ✅ **レポート生成システム** (`app/services/reporting_service.py`)
- ✅ **ユーザー管理・権限制御・監査ログ** (7管理エンドポイント)

#### 3. 外部取引所統合（立花証券API）
- ✅ **リアルタイム取引執行** (`app/services/tachibana_client.py`)
- ✅ **注文管理システム** (注文ライフサイクル・自動監視)
- ✅ **口座管理・残高照会** (ポジション同期・証拠金管理)
- ✅ **リスク管理・取引限度額** (9取引統合エンドポイント)

#### 4. フロントエンド統合準備
- ✅ **TypeScript型定義自動生成** (`scripts/generate_types.py`)
- ✅ **OpenAPI仕様書完全対応** (Swagger/Redoc)
- ✅ **フロントエンド支援API** (9開発支援エンドポイント)
- ✅ **WebSocket統合準備** (接続情報・サンプルデータ)

### 🔧 現在の稼働状況・次期開発注意点

#### 稼働中サービス（Phase 2C完了時点）
```bash
# 確認済み稼働サービス
- FastAPI: 79エンドポイント稼働（Phase 2Cで27エンドポイント追加）
- PostgreSQL: 5テーブル・122カラム・制約設定完了
- Redis: セッション・キャッシュ・Pub/Sub機能
- WebSocket: リアルタイム配信基盤
- Celery: 19タスク（AI・バックテスト・市場データ・通知・テクニカル指標）
- yfinance: 日本株10銘柄・テクニカル指標・企業情報
- AI分析: マルチモデル合意システム（GPT-4/Claude/Gemini）
- 管理システム: 監視・レポート・ユーザー管理完備
- 取引統合: 立花証券APIモック・実取引準備完了

# 開発環境確認コマンド
cd /Users/kazusa/Develop/kaboom/api
uv run uvicorn app.main:app --reload  # APIサーバー起動
curl http://localhost:8000/api/v1/health  # ヘルスチェック
curl http://localhost:8000/docs  # Swagger UI確認
uv run python scripts/generate_types.py  # TypeScript型定義生成
```

#### Phase 3A開発時重要事項（Next.js 15フロントエンド）
- **API基盤完成**: 79エンドポイント・完全なOpenAPI仕様書・型定義準備完了
- **認証統合**: Supabase認証・JWT検証・権限制御システム稼働中
- **リアルタイム**: WebSocket・Redis Pub/Sub・自動再接続機能
- **開発支援**: TypeScript型定義自動生成・サンプルデータ・開発ツール完備

### 🗂️ 重要ファイル・設定状況

#### 実装完了ファイル
- `app/services/redis_client.py` - Redis統合クライアント
- `app/websocket/manager.py` - WebSocket接続管理
- `app/tasks/` - 全Celeryタスク実装
- `app/routers/portfolios.py` - ポートフォリオAPI
- `app/routers/trades.py` - 取引API
- `app/routers/health.py` - 拡張ヘルスチェック

#### 環境変数設定状況
- ✅ `OPENROUTER_API_KEY`: AI機能実動作確認済み
- ✅ `SUPABASE_URL`, `SUPABASE_ANON_KEY`: 接続確認済み  
- ✅ `REDIS_URL`: Redis接続・機能動作確認済み
- ✅ `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`: Redis統合済み