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

Since the codebase is in planning phase, here are the expected commands once implementation begins:

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

## 🎯 Phase 1 実装完了状況 (2025-09-08)

### ✅ 完了済み実装
**OpenRouter AI統合基盤:**
- ✅ `app/services/openrouter_client.py` - 完全なAIクライアント実装
- ✅ GPT-4, Claude, Gemini等マルチモデル対応
- ✅ フォールバック機能（モデル障害時自動切り替え）
- ✅ コスト計算・使用量追跡機能
- ✅ 実証済み: GPT-3.5 ($0.000485), GPT-4 ($0.007990)

**認証・セキュリティ基盤:**
- ✅ `app/middleware/auth.py` - JWT認証・RBAC実装
- ✅ `app/middleware/rate_limit.py` - 役割別レート制限
- ✅ `app/middleware/security.py` - XSS/CSRF保護
- ✅ Supabase認証統合完了・接続確認済み

**API エンドポイント:**
- ✅ `app/routers/health.py` - Kubernetes対応ヘルスチェック
- ✅ `app/routers/auth.py` - 認証・セッション管理API
- ✅ `app/routers/ai_analysis.py` - AI分析API（認証保護済み）
- ✅ FastAPI統合: 完全な起動・リクエスト処理確認済み

### 📋 次期セッション優先実装項目

#### Phase 2A: バックグラウンドタスク基盤 (最高優先度)
1. **Redis統合**: WebSocket・キャッシュ・ジョブキューの基盤
2. **Celeryタスク実装**: AI分析の非同期処理
3. **AI分析ジョブワーカー**: 実際のジョブ実行・結果配信

#### Phase 2B: コア機能API (高優先度)  
4. **ポートフォリオAPI**: 投資組み合わせ管理
5. **取引API**: 売買注文・履歴管理
6. **チャート生成**: matplotlib/mplfinance統合

#### Phase 2C: 拡張機能 (中優先度)
7. **バックテスト基盤**: AI戦略評価システム
8. **WebSocket実装**: リアルタイム更新配信
9. **管理機能**: 使用量ダッシュボード・監視

### 🔧 次期開発時の重要な注意点

#### 実装パターン (必ず従うこと)
```bash
# 開発開始前の確認
cd /Users/kazusa/Develop/kaboom/api
uv run python -c "import app.main; print('Import successful')"  # 基本動作確認
uv run python -c "from app.services.openrouter_client import OpenRouterClient; print('OpenRouter ready')"  # AI機能確認
```

#### 環境変数設定済み状況
- ✅ `OPENROUTER_API_KEY`: 実動作確認済み  
- ✅ `SUPABASE_URL`, `SUPABASE_ANON_KEY`: 接続確認済み
- ⚠️ `REDIS_URL`: 未接続（localhost:6379 connection refused）

#### 既存の実装アーキテクチャを維持
- **OpenRouter統一戦略**: 全AI機能は`OpenRouterClient`経由で実装
- **FastAPI構造**: `app/routers/`配下でAPIエンドポイント分離
- **ミドルウェア順序**: CORS → Security → RateLimit の順序を維持
- **認証依存関数**: `get_current_user`, `get_premium_user`等を活用

#### テスト実行パターン
```python
# FastAPI起動テスト
uv run python -c "
from app.main import app
import uvicorn
import threading
import time
server_thread = threading.Thread(target=lambda: uvicorn.run(app, host='127.0.0.1', port=8001), daemon=True)
server_thread.start()
time.sleep(3)
# テスト実行
"
```