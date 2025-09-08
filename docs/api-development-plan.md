# Kaboom株式自動売買システム - API開発計画書

## 1. 方針決定事項

### 1.1 AI統合アーキテクチャ
**OpenRouter統一戦略を採用**

- **統合AI API**: OpenRouter（https://openrouter.ai/）を単一エンドポイントとして使用
- **モデル切り替え**: API呼び出し時のモデル指定で簡単に切り替え可能
- **対応モデル例**: 
  - `openai/gpt-4-turbo-preview`
  - `google/gemini-pro-vision`
  - `anthropic/claude-3-sonnet`
  - `meta-llama/llama-2-70b-chat`
- **利点**: 
  - 単一API KEY管理
  - 統一されたレスポンス形式
  - モデル比較・切り替えが容易
  - コスト管理の一元化

### 1.2 実装優先度
1. **OpenRouter統合基盤** (Week 1)
2. **基本API契約定義** (Week 1-2) 
3. **非同期ジョブ設計** (Week 2)
4. **認証・セキュリティ** (Week 3)

## 2. 標準ドキュメント体系

### 2.1 ディレクトリ構成

```
api/
├── docs/                    # 📚 標準ドキュメント体系
│   ├── api/                 # 外部公開インタフェース
│   │   ├── openapi.yaml     # HTTP API契約
│   │   ├── asyncapi.yaml    # WebSocket/Redis契約  
│   │   └── error-catalog.md # RFC7807準拠エラー体系
│   ├── ai/                  # AI統合設計（OpenRouter）
│   │   ├── openrouter-integration.md
│   │   ├── model-comparison-matrix.md
│   │   └── prompt-templates/
│   │       ├── technical-analysis.md
│   │       ├── market-sentiment.md
│   │       └── risk-assessment.md
│   ├── data/                # ドメイン&データ設計
│   │   ├── er-diagram.drawio
│   │   ├── schema.md
│   │   └── migration-plan.md
│   ├── async/               # 非同期タスク設計
│   │   ├── job-specifications/
│   │   │   ├── ai-analysis-job.md
│   │   │   ├── backtest-job.md
│   │   │   └── market-data-job.md
│   │   └── job-states.drawio
│   ├── security/            # セキュリティ設計
│   │   ├── auth-design.md
│   │   ├── rbac-model.md
│   │   └── api-key-management.md
│   ├── nonfunctional/       # 非機能要求
│   │   ├── slo.md
│   │   └── capacity-planning.md
│   ├── ops/                 # 運用ドキュメント
│   │   ├── observability.md
│   │   └── runbook.md
│   ├── architecture/        # アーキテクチャ
│   │   ├── context-diagram.drawio
│   │   ├── sequence-diagrams/
│   │   └── adr/
│   │       ├── 0001-openrouter-ai-integration.md
│   │       ├── 0002-websocket-redis-pubsub.md
│   │       └── 0003-supabase-auth-strategy.md
│   └── quality/             # 品質保証
│       ├── test-strategy.md
│       └── contract-testing.md
```

## 3. Phase 1: 基盤ドキュメント作成（Week 1）

### 3.1 最優先タスク

#### Task 1.1: OpenRouter統合設計書
**ファイル**: `docs/ai/openrouter-integration.md`

**内容**:
```markdown
# OpenRouter統合設計

## 基本設定
- API Endpoint: https://openrouter.ai/api/v1
- 認証: Bearer Token（OPENROUTER_API_KEY）
- レート制限: 統合管理

## モデル設定
primary_models:
  - technical_analysis: "openai/gpt-4-turbo-preview"
  - market_sentiment: "anthropic/claude-3-sonnet"
  - risk_assessment: "google/gemini-pro-vision"

fallback_models:
  - "meta-llama/llama-2-70b-chat"

## API呼び出し例
POST https://openrouter.ai/api/v1/chat/completions
{
  "model": "openai/gpt-4-turbo-preview",
  "messages": [...],
  "temperature": 0.1
}
```

#### Task 1.2: エラーカタログ
**ファイル**: `docs/api/error-catalog.md`

**Kaboom特化エラー定義**:
```markdown
## AI関連エラー（OpenRouter）
- `OPENROUTER_RATE_LIMIT` (429): レート制限超過
- `OPENROUTER_MODEL_UNAVAILABLE` (503): 指定モデル利用不可
- `AI_ANALYSIS_TIMEOUT` (408): AI分析タイムアウト
- `PROMPT_VALIDATION_FAILED` (422): プロンプト形式エラー

## 取引関連エラー  
- `INSUFFICIENT_BALANCE` (400): 残高不足
- `MARKET_CLOSED` (409): 市場時間外取引
- `INVALID_SYMBOL` (422): 無効銘柄コード

## バックテストエラー
- `BACKTEST_DATA_INSUFFICIENT` (422): データ不足
- `BACKTEST_TIMEOUT` (408): 処理時間超過
```

#### Task 1.3: 重要な意思決定記録
**ファイル**: `docs/architecture/adr/0001-openrouter-ai-integration.md`

```markdown
# ADR-0001: OpenRouter統一AI統合

## Status: ACCEPTED

## Context
複数のAIプロバイダー（OpenAI, Google, Anthropic）を効率的に管理し、
モデルの切り替えやコスト管理を簡素化する必要がある。

## Decision
OpenRouterを単一の統合APIとして採用

## Rationale
✅ 単一API KEY管理
✅ 統一レスポンス形式  
✅ 20+ モデルサポート
✅ 使用量・コスト一元管理
✅ フォールバック機能

## Consequences
✅ 開発効率向上
✅ 運用コスト削減
❌ OpenRouter依存リスク
❌ 若干のレイテンシ増加
```

### 3.2 API基本契約定義

#### Task 1.4: OpenAPI仕様骨子
**ファイル**: `docs/api/openapi.yaml`

```yaml
openapi: 3.0.3
info:
  title: Kaboom Stock Trading API
  version: 1.0.0
  description: Real-time stock trading with AI analysis

paths:
  # 認証 (Supabase)
  /api/v1/auth/verify:
    post:
      summary: JWT token verification
      
  # AI分析 (OpenRouter統合)
  /api/v1/ai/analyze:
    post:
      summary: Trigger AI analysis
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                symbol:
                  type: string
                  example: "7203"
                models:
                  type: array
                  items:
                    type: string
                  example: ["openai/gpt-4-turbo-preview", "anthropic/claude-3-sonnet"]
                analysis_types:
                  type: array
                  items:
                    type: string
                  example: ["technical", "sentiment", "risk"]
      responses:
        "202":
          description: Analysis queued
          headers:
            Location:
              schema:
                type: string
                format: uri
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id:
                    type: string
                    format: uuid
                  estimated_completion:
                    type: string
                    format: date-time

components:
  schemas:
    AIAnalysisResult:
      type: object
      properties:
        analysis_id:
          type: string
          format: uuid
        symbol:
          type: string
        model_results:
          type: array
          items:
            type: object
            properties:
              model:
                type: string
              decision:
                type: string
                enum: ["buy", "sell", "hold"]
              confidence:
                type: number
                minimum: 0
                maximum: 1
              reasoning:
                type: string
```

## 4. Phase 2: 非同期ジョブ設計（Week 2）

### 4.1 AI分析ジョブ仕様（OpenRouter対応）

#### Task 2.1: AI分析ジョブ仕様書
**ファイル**: `docs/async/job-specifications/ai-analysis-job.md`

```markdown
# AI Analysis Job Spec v1 (OpenRouter Integration)

## Purpose
OpenRouterを通じて複数AIモデルで株価分析を実行

## Input Schema
{
  "symbol": "7203",
  "models": [
    "openai/gpt-4-turbo-preview",
    "anthropic/claude-3-sonnet",
    "google/gemini-pro-vision"
  ],
  "analysis_types": ["technical", "sentiment", "risk"],
  "timeframes": ["1h", "4h", "1d"],
  "user_id": "uuid"
}

## Processing Flow
1. Market data collection (yfinance)
2. Chart generation (matplotlib)
3. Parallel AI analysis (OpenRouter)
   - Model A: Technical analysis
   - Model B: Sentiment analysis  
   - Model C: Risk assessment
4. Result aggregation
5. WebSocket notification

## State Machine
queued → data_fetching → chart_generation → ai_processing → result_aggregation → completed/failed

## SLA
- Timeout: 3分（複数モデル並列実行）
- Target: P95 < 90秒

## Idempotency
Natural Key: (symbol, models_hash, analysis_date)

## Output Schema
{
  "analysis_id": "uuid",
  "symbol": "7203",
  "model_results": [
    {
      "model": "openai/gpt-4-turbo-preview",
      "analysis_type": "technical", 
      "decision": "buy",
      "confidence": 0.85,
      "reasoning": "RSI oversold, MACD bullish crossover",
      "cost_usd": 0.023
    }
  ],
  "aggregated_decision": {
    "final_decision": "buy",
    "consensus_confidence": 0.78,
    "model_agreement": 0.67
  },
  "execution_metrics": {
    "total_cost_usd": 0.067,
    "processing_time_seconds": 45,
    "models_used": 3
  }
}
```

### 4.2 バックテストジョブ仕様（AI統合）

#### Task 2.2: バックテストジョブ仕様書
**ファイル**: `docs/async/job-specifications/backtest-job.md`

```markdown
# Backtest Job Spec v1 (OpenRouter AI Integration)

## Purpose
OpenRouterのAIモデルを使用したバックテスト実行

## Input Schema
{
  "strategy_config": {
    "name": "multi_ai_consensus",
    "ai_models": [
      "openai/gpt-4-turbo-preview",
      "anthropic/claude-3-sonnet"
    ],
    "consensus_threshold": 0.7,
    "decision_weight": {
      "technical": 0.4,
      "sentiment": 0.3, 
      "risk": 0.3
    }
  },
  "simulation_config": {
    "symbols": ["7203", "9984"],
    "start_date": "2023-01-01",
    "end_date": "2024-01-01",
    "initial_capital": 1000000,
    "commission_rate": 0.001
  },
  "user_id": "uuid"
}

## Processing Flow
1. Historical data preparation
2. Time-series simulation loop:
   - For each trading day:
     - Generate market context
     - AI analysis (OpenRouter)
     - Decision aggregation
     - Trade execution simulation
3. Performance calculation
4. Report generation

## Progress Tracking
GET /api/v1/backtest/status/{job_id}
{
  "status": "simulation_running",
  "progress": {
    "current_date": "2023-06-15",
    "completion_percent": 45.2,
    "estimated_remaining": "00:12:30"
  },
  "intermediate_results": {
    "current_balance": 1156780,
    "total_trades": 89,
    "win_rate": 0.67,
    "ai_cost_usd": 45.67
  }
}
```

## 5. Phase 3: セキュリティ・運用（Week 3）

### 5.1 認証設計

#### Task 3.1: 認証設計書
**ファイル**: `docs/security/auth-design.md`

```markdown
# 認証設計（Supabase + OpenRouter）

## JWT認証フロー
1. Frontend: Supabase Auth login
2. Backend: JWT validation via Supabase
3. OpenRouter API: Server-to-server auth

## API Key管理
- Supabase JWT: ユーザー認証
- OpenRouter API Key: サーバーサイド管理（環境変数）
- 立花証券 API: ユーザー別暗号化保存

## 権限管理（RBAC）
- user: 基本AI分析（月100回）
- premium: 高頻度分析（月1000回）、複数モデル比較
- admin: システム管理、全ユーザーデータ参照
```

### 5.2 コスト管理・監視

#### Task 3.2: 運用監視設計
**ファイル**: `docs/ops/observability.md`

```markdown
# 運用監視（OpenRouter統合）

## コスト監視メトリクス
- openrouter_api_calls_total
- openrouter_cost_usd_total (by model)
- ai_analysis_duration_seconds
- model_success_rate (by provider)

## アラート設定
- Daily AI cost > $100
- Model failure rate > 5%
- Analysis timeout > 10%

## ダッシュボード
- リアルタイムAI使用量
- モデル別パフォーマンス比較
- コスト効率分析
```

## 6. 実装スケジュール

### Week 1: 基盤文書・実装完了 ✅
- [x] OpenRouter統合設計
- [x] エラーカタログ
- [x] ADR (OpenRouter採用理由)
- [x] OpenAPI仕様骨子
- [x] **実装完了**: OpenRouter統合基盤
- [x] **実装完了**: 認証・セキュリティミドルウェア
- [x] **実装完了**: 基本APIエンドポイント
- [x] **テスト完了**: 実際のAI分析動作確認

### 📊 Phase 1 実装実績 (2025-09-08完了)
**🎯 実装済み機能:**
- ✅ OpenRouterクライアント (app/services/openrouter_client.py) - GPT-4/Claude/Gemini対応
- ✅ フォールバック機能 - モデル障害時自動切り替え
- ✅ JWT認証・RBAC (app/middleware/auth.py) - Basic/Premium/Enterprise/Admin
- ✅ レート制限 (app/middleware/rate_limit.py) - 役割別制限
- ✅ セキュリティミドルウェア (app/middleware/security.py) - XSS/CSRF保護
- ✅ ヘルスチェックAPI (app/routers/health.py) - Kubernetes対応
- ✅ AI分析API (app/routers/ai_analysis.py) - 非同期ジョブ対応
- ✅ 認証API (app/routers/auth.py) - Supabase統合

**🧪 実証済みテスト:**
- ✅ OpenRouter実API接続: GPT-3.5 ($0.000485), GPT-4 ($0.007990)
- ✅ Supabase認証統合: JWT検証・セッション管理
- ✅ セキュリティ保護: 全エンドポイント適切な認証要求
- ✅ FastAPI統合: 完全な起動・リクエスト処理

### Week 2: 非同期・コア機能実装 🔄
- [x] AI分析ジョブ仕様
- [x] バックテストジョブ仕様  
- [ ] **次期実装**: Celeryバックグラウンドタスク統合
- [ ] **次期実装**: ポートフォリオ・取引API
- [ ] **次期実装**: チャート生成サービス
- [ ] AsyncAPI仕様（WebSocket）

### Week 3: 拡張機能・運用
- [x] 認証設計書
- [x] 権限管理モデル
- [x] 監視・アラート設計
- [ ] **次期実装**: バックテストエンジン
- [ ] **次期実装**: WebSocketリアルタイム機能
- [ ] **次期実装**: 使用量ダッシュボード

### Week 4: 統合・最適化
- [x] OpenRouter統合ライブラリ ✅
- [x] 基本API実装 ✅
- [ ] **次期実装**: Celeryタスク実装
- [ ] **次期実装**: Redis統合
- [ ] **次期実装**: 立花証券API統合

## 7. 次のアクション

この計画書を元に、以下から着手を推奨します：

1. **ADR-0001作成** - OpenRouter採用の技術的根拠を文書化
2. **エラーカタログ作成** - API実装の基盤となるエラー処理統一
3. **OpenRouter統合設計** - AI機能の核となる統合設計
4. **OpenAPI仕様策定** - フロントエンド連携の契約定義

どのタスクから開始しますか？