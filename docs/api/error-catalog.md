# Kaboom API エラーカタログ

## Overview

本文書はKaboom株式自動売買システムAPIで発生する全エラーの標準化されたカタログです。
RFC 7807 (Problem Details for HTTP APIs)に準拠したエラー形式を採用し、クライアント側での適切なエラーハンドリングを支援します。

## エラーレスポンス形式（RFC 7807準拠）

```json
{
  "type": "https://kaboom-api.com/problems/insufficient-balance",
  "title": "Insufficient Balance",
  "status": 400,
  "detail": "Account balance (¥50,000) is insufficient for trade amount (¥100,000)",
  "instance": "/api/v1/trades/abc123",
  "timestamp": "2024-08-24T12:00:00Z",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "context": {
    "user_id": "user123",
    "portfolio_id": "port456",
    "requested_amount": 100000,
    "available_balance": 50000
  }
}
```

## エラー分類体系

### 1. 認証・認可エラー (4xx)

#### 401 Unauthorized

| Error Code | Type URI | Title | Description | Retry | 
|------------|----------|-------|-------------|-------|
| `AUTH_TOKEN_MISSING` | `/problems/auth/token-missing` | Missing Authentication Token | Authorization headerにBearerトークンが含まれていない | ❌ |
| `AUTH_TOKEN_INVALID` | `/problems/auth/token-invalid` | Invalid Authentication Token | JWTトークンの形式が無効または署名検証失敗 | ❌ |
| `AUTH_TOKEN_EXPIRED` | `/problems/auth/token-expired` | Authentication Token Expired | JWTトークンの有効期限切れ | ✅ (refresh) |
| `SUPABASE_AUTH_ERROR` | `/problems/auth/supabase-error` | Supabase Authentication Error | Supabase認証サービスとの連携エラー | ✅ |

#### 403 Forbidden

| Error Code | Type URI | Title | Description | Retry |
|------------|----------|-------|-------------|-------|
| `INSUFFICIENT_PRIVILEGES` | `/problems/auth/insufficient-privileges` | Insufficient Privileges | ユーザーの権限レベルが不十分（premium機能にbasicユーザーがアクセス等） | ❌ |
| `RESOURCE_ACCESS_DENIED` | `/problems/auth/resource-access-denied` | Resource Access Denied | 他ユーザーのリソースへの不正アクセス | ❌ |
| `API_QUOTA_EXCEEDED` | `/problems/auth/quota-exceeded` | API Quota Exceeded | ユーザーのAPI使用制限超過 | ✅ (wait) |

### 2. バリデーションエラー (4xx)

#### 400 Bad Request

| Error Code | Type URI | Title | Description | Retry |
|------------|----------|-------|-------------|-------|
| `INVALID_REQUEST_FORMAT` | `/problems/validation/invalid-format` | Invalid Request Format | JSON形式不正またはContent-Type不正 | ❌ |
| `MISSING_REQUIRED_FIELD` | `/problems/validation/missing-field` | Missing Required Field | 必須フィールドの欠如 | ❌ |
| `INVALID_FIELD_VALUE` | `/problems/validation/invalid-value` | Invalid Field Value | フィールド値の形式・範囲エラー | ❌ |
| `INSUFFICIENT_BALANCE` | `/problems/trading/insufficient-balance` | Insufficient Balance | 取引に必要な残高不足 | ❌ |

#### 422 Unprocessable Entity  

| Error Code | Type URI | Title | Description | Retry |
|------------|----------|-------|-------------|-------|
| `INVALID_SYMBOL` | `/problems/market/invalid-symbol` | Invalid Stock Symbol | 存在しない・サポート外の銘柄コード | ❌ |
| `INVALID_TIMEFRAME` | `/problems/market/invalid-timeframe` | Invalid Timeframe | サポート外の時間軸指定 | ❌ |
| `MARKET_CLOSED` | `/problems/trading/market-closed` | Market Closed | 市場時間外の取引要求 | ✅ (schedule) |
| `TRADE_AMOUNT_LIMITS` | `/problems/trading/amount-limits` | Trade Amount Limits | 最小・最大取引金額制限違反 | ❌ |

### 3. AI分析関連エラー (4xx/5xx)

#### 429 Too Many Requests

| Error Code | Type URI | Title | Description | Retry |
|------------|----------|-------|-------------|-------|
| `OPENROUTER_RATE_LIMIT` | `/problems/ai/openrouter-rate-limit` | OpenRouter Rate Limit Exceeded | OpenRouterのレート制限超過 | ✅ (exponential backoff) |
| `AI_QUOTA_EXCEEDED` | `/problems/ai/quota-exceeded` | AI Analysis Quota Exceeded | ユーザーのAI分析回数制限超過 | ✅ (upgrade/wait) |

#### 400 Bad Request

| Error Code | Type URI | Title | Description | Retry |
|------------|----------|-------|-------------|-------|
| `INVALID_AI_MODEL` | `/problems/ai/invalid-model` | Invalid AI Model | サポート外のAIモデル指定 | ❌ |
| `PROMPT_VALIDATION_FAILED` | `/problems/ai/prompt-validation` | Prompt Validation Failed | AIプロンプトの形式・内容エラー | ❌ |
| `ANALYSIS_TYPE_UNSUPPORTED` | `/problems/ai/analysis-type-unsupported` | Analysis Type Unsupported | サポート外の分析タイプ | ❌ |

#### 408 Request Timeout

| Error Code | Type URI | Title | Description | Retry |
|------------|----------|-------|-------------|-------|
| `AI_ANALYSIS_TIMEOUT` | `/problems/ai/analysis-timeout` | AI Analysis Timeout | AI分析処理のタイムアウト | ✅ |
| `CHART_GENERATION_TIMEOUT` | `/problems/ai/chart-timeout` | Chart Generation Timeout | チャート生成処理のタイムアウト | ✅ |

#### 500/502/503 Server Errors

| Error Code | Type URI | Title | Description | Retry |
|------------|----------|-------|-------------|-------|
| `OPENROUTER_API_ERROR` | `/problems/ai/openrouter-error` | OpenRouter API Error | OpenRouterサービスエラー | ✅ (backoff) |
| `OPENROUTER_MODEL_UNAVAILABLE` | `/problems/ai/model-unavailable` | AI Model Temporarily Unavailable | 指定AIモデルが一時利用不可 | ✅ (fallback) |
| `CHART_GENERATION_FAILED` | `/problems/ai/chart-generation-failed` | Chart Generation Failed | matplotlib/mplfinanceによるチャート生成失敗 | ✅ |

### 4. バックテスト関連エラー (4xx/5xx)

#### 422 Unprocessable Entity

| Error Code | Type URI | Title | Description | Retry |
|------------|----------|-------|-------------|-------|
| `BACKTEST_DATA_INSUFFICIENT` | `/problems/backtest/insufficient-data` | Insufficient Historical Data | 指定期間の履歴データ不足 | ❌ |
| `BACKTEST_PERIOD_INVALID` | `/problems/backtest/invalid-period` | Invalid Backtest Period | 無効なバックテスト期間（未来日付、期間過長等） | ❌ |
| `STRATEGY_CONFIG_INVALID` | `/problems/backtest/invalid-strategy` | Invalid Strategy Configuration | 戦略設定の不正（パラメータ範囲外等） | ❌ |

#### 408 Request Timeout

| Error Code | Type URI | Title | Description | Retry |
|------------|----------|-------|-------------|-------|
| `BACKTEST_TIMEOUT` | `/problems/backtest/timeout` | Backtest Execution Timeout | バックテスト処理のタイムアウト（通常30分） | ❌ |

#### 503 Service Unavailable  

| Error Code | Type URI | Title | Description | Retry |
|------------|----------|-------|-------------|-------|
| `BACKTEST_QUEUE_FULL` | `/problems/backtest/queue-full` | Backtest Queue Full | バックテストキューの満杯 | ✅ (delay) |
| `COMPUTATIONAL_RESOURCES_UNAVAILABLE` | `/problems/backtest/resources-unavailable` | Computational Resources Unavailable | 計算リソース不足 | ✅ (delay) |

### 5. 外部API連携エラー (5xx)

#### 502 Bad Gateway

| Error Code | Type URI | Title | Description | Retry |
|------------|----------|-------|-------------|-------|
| `TACHIBANA_API_ERROR` | `/problems/external/tachibana-error` | Tachibana Securities API Error | 立花証券APIとの連携エラー | ✅ (limited) |
| `YFINANCE_API_ERROR` | `/problems/external/yfinance-error` | yfinance API Error | yfinance経由の価格データ取得エラー | ✅ |

#### 503 Service Unavailable

| Error Code | Type URI | Title | Description | Retry |
|------------|----------|-------|-------------|-------|
| `YFINANCE_DATA_UNAVAILABLE` | `/problems/external/yfinance-unavailable` | Market Data Unavailable | 価格データ取得サービス利用不可 | ✅ (delay) |
| `EXTERNAL_SERVICE_MAINTENANCE` | `/problems/external/maintenance` | External Service Under Maintenance | 外部サービスメンテナンス中 | ✅ (schedule) |

### 6. システムエラー (5xx)

#### 500 Internal Server Error

| Error Code | Type URI | Title | Description | Retry |
|------------|----------|-------|-------------|-------|
| `DATABASE_CONNECTION_ERROR` | `/problems/system/database-error` | Database Connection Error | データベース接続エラー | ✅ (backoff) |
| `REDIS_CONNECTION_ERROR` | `/problems/system/redis-error` | Redis Connection Error | Redis接続エラー（キャッシュ・PubSub） | ✅ |
| `CELERY_TASK_ERROR` | `/problems/system/task-error` | Background Task Error | Celeryバックグラウンドタスクエラー | ✅ |
| `WEBSOCKET_BROADCAST_FAILED` | `/problems/system/websocket-error` | WebSocket Broadcast Failed | WebSocket配信エラー | ✅ |

#### 503 Service Unavailable

| Error Code | Type URI | Title | Description | Retry |
|------------|----------|-------|-------------|-------|
| `SERVICE_OVERLOADED` | `/problems/system/overloaded` | Service Overloaded | システム過負荷状態 | ✅ (backoff) |
| `MAINTENANCE_MODE` | `/problems/system/maintenance` | Service Under Maintenance | システムメンテナンス中 | ✅ (schedule) |

## エラーレスポンス例

### AI分析リクエストでのOpenRouterレート制限

```json
{
  "type": "https://kaboom-api.com/problems/ai/openrouter-rate-limit",
  "title": "OpenRouter Rate Limit Exceeded", 
  "status": 429,
  "detail": "OpenRouter API rate limit exceeded. Current limit: 20 req/min, retry after 45 seconds",
  "instance": "/api/v1/ai/analyze",
  "timestamp": "2024-08-24T12:30:00Z",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "context": {
    "model": "openai/gpt-4-turbo-preview", 
    "retry_after_seconds": 45,
    "current_limit": "20 req/min",
    "reset_time": "2024-08-24T12:31:00Z"
  }
}
```

### バックテスト用データ不足エラー

```json
{
  "type": "https://kaboom-api.com/problems/backtest/insufficient-data",
  "title": "Insufficient Historical Data",
  "status": 422,
  "detail": "Insufficient data for symbol 7203 in period 2020-01-01 to 2024-01-01. Available data starts from 2021-03-15",
  "instance": "/api/v1/backtest/run",
  "timestamp": "2024-08-24T12:45:00Z", 
  "trace_id": "550e8400-e29b-41d4-a716-446655440001",
  "context": {
    "symbol": "7203",
    "requested_start": "2020-01-01",
    "requested_end": "2024-01-01", 
    "available_start": "2021-03-15",
    "missing_days": 438
  }
}
```

## クライアント側エラーハンドリングガイドライン

### 基本パターン

```typescript
interface APIError {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  timestamp: string;
  trace_id: string;
  context?: Record<string, any>;
}

async function handleAPIError(error: APIError): Promise<void> {
  // トレースIDをログに記録
  console.error(`API Error [${error.trace_id}]: ${error.title}`, error);
  
  // エラータイプ別の処理
  switch (error.type) {
    case 'https://kaboom-api.com/problems/auth/token-expired':
      await refreshAuthToken();
      break;
      
    case 'https://kaboom-api.com/problems/ai/openrouter-rate-limit':
      const retryAfter = error.context?.retry_after_seconds || 60;
      setTimeout(() => retryRequest(), retryAfter * 1000);
      break;
      
    case 'https://kaboom-api.com/problems/trading/market-closed':
      showUserNotification('市場時間外です。市場開始時刻まで取引はできません。');
      break;
      
    default:
      showGenericErrorMessage(error.title, error.detail);
  }
}
```

### リトライ戦略

```typescript
const RETRY_CONFIG = {
  'openrouter-rate-limit': { 
    maxRetries: 3, 
    baseDelay: 1000, 
    backoff: 'exponential' 
  },
  'database-error': { 
    maxRetries: 5, 
    baseDelay: 500, 
    backoff: 'exponential' 
  },
  'yfinance-unavailable': { 
    maxRetries: 2, 
    baseDelay: 5000, 
    backoff: 'linear' 
  }
};
```

## 監視・アラート

### エラー率メトリクス

```prometheus
# システムエラー率（5xx系）
system_error_rate = sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# AI API エラー率
ai_error_rate = sum(rate(openrouter_requests_total{status!="200"}[5m])) / sum(rate(openrouter_requests_total[5m]))

# 外部API エラー率  
external_api_error_rate = sum(rate(external_api_requests_total{status!="200"}[5m])) / sum(rate(external_api_requests_total[5m]))
```

### アラート条件

- システムエラー率 > 1% (5分間)
- AI APIエラー率 > 5% (10分間)  
- 外部APIエラー率 > 10% (15分間)
- 特定エラー（`BACKTEST_TIMEOUT`等）の頻発

## 更新履歴

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-08-24 | 初版作成（OpenRouter統合対応） |

## 関連文書

- [ADR-0001: OpenRouter AI統合戦略](../architecture/adr/0001-openrouter-ai-integration.md)
- [OpenAPI Specification](./openapi.yaml) - 予定
- [運用監視ガイド](../ops/observability.md) - 予定