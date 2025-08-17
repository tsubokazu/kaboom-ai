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
- **AI Processing**: LangGraph workflows with multiple AI agents (market analysis, technical analysis, decision making)
- **Real-time**: WebSocket + Redis Pub/Sub for real-time data distribution
- **External APIs**: Integration with trading APIs (立花証券), market data (yfinance), AI providers (OpenAI, Gemini)
- **Background Tasks**: Celery for heavy processing (backtests, AI analysis, market data updates)
- **Charts**: matplotlib + mplfinance for generating chart images served to frontend

### Data Flow
1. **Authentication**: Supabase handles auth, backend validates JWT tokens
2. **Real-time Data**: Market data flows through WebSocket connections managed by Redis Pub/Sub
3. **AI Analysis**: LangGraph workflows process market data through multiple AI agents
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

### AI Processing Pipeline
- LangGraph workflows coordinate multiple AI agents
- Chart generation happens server-side using matplotlib/mplfinance
- AI decisions are cached and distributed via WebSocket
- Multiple AI providers (OpenAI, Gemini) for decision comparison

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

### Pre-Push Requirements
Always ensure the following passes before pushing:

**Frontend (web/):**
```bash
cd web
npm run lint        # ESLint checks must pass
npm run type-check  # TypeScript compilation must succeed
npm run test        # All unit tests must pass
npm run build       # Production build must succeed
```

**Backend (api/):**
```bash
cd api
black --check .     # Code formatting must be correct
isort --check-only . # Import sorting must be correct
mypy .              # Type checking must pass
pytest              # All tests must pass
```

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

## Important File Locations

- **Design Documents**: `docs/` - Contains comprehensive system design and development phases
- **Frontend Planning**: `docs/web_application_planning.md` - Detailed frontend specifications
- **Backend Planning**: Second half of `docs/web_application_planning.md` - API and system design
- **Architecture**: `docs/directory_structure_design.md` - Complete directory structure with rationale

When implementing, follow the detailed specifications in the docs folder, particularly the component architecture in the directory structure design and the phased development approach outlined in the development phases plan.