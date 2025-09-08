# AI Analysis Job Specification v1.0

## Overview

OpenRouter統合による株式AI分析ジョブの詳細仕様書です。
複数AIモデル（GPT-4, Claude, Gemini等）を並列実行し、合意形成による高精度な売買判断を提供します。

## Job Purpose

指定銘柄について、複数のAIモデルで以下の分析を実行：
- **テクニカル分析**: チャートパターン・指標解析
- **センチメント分析**: ニュース・市場感情分析  
- **リスク評価**: ボラティリティ・リスク要因分析
- **合意形成**: 複数モデルの判断を統合し最終決定

## Input Schema

### JSON Input Format
```json
{
  "symbol": "7203",
  "symbol_name": "トヨタ自動車",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "analysis_config": {
    "types": ["technical", "sentiment", "risk"],
    "models": [
      {
        "provider": "openai/gpt-4-turbo-preview",
        "analysis_type": "technical",
        "temperature": 0.1
      },
      {
        "provider": "anthropic/claude-3-sonnet",
        "analysis_type": "sentiment", 
        "temperature": 0.2
      },
      {
        "provider": "google/gemini-pro-vision",
        "analysis_type": "risk",
        "temperature": 0.1
      }
    ]
  },
  "market_context": {
    "timeframes": ["1h", "4h", "1d"],
    "include_chart": true,
    "chart_config": {
      "width": 800,
      "height": 600,
      "indicators": ["RSI", "MACD", "BB"]
    }
  },
  "user_preferences": {
    "risk_tolerance": "medium",
    "investment_horizon": "short_term",
    "priority": "normal"
  }
}
```

### Input Validation Rules
```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum

class AnalysisType(str, Enum):
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    RISK = "risk"

class RiskTolerance(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ModelConfig(BaseModel):
    provider: str = Field(..., regex=r'^[a-zA-Z0-9\-_]+/[a-zA-Z0-9\-_\.]+$')
    analysis_type: AnalysisType
    temperature: float = Field(0.1, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=100, le=4000)

class MarketContext(BaseModel):
    timeframes: List[str] = Field(["1h", "4h", "1d"], min_items=1, max_items=6)
    include_chart: bool = True
    chart_config: Optional[Dict[str, Any]] = None
    
    @validator('timeframes')
    def validate_timeframes(cls, v):
        valid_frames = ['1m', '5m', '15m', '1h', '4h', '1d', '1w']
        for frame in v:
            if frame not in valid_frames:
                raise ValueError(f'Invalid timeframe: {frame}')
        return v

class UserPreferences(BaseModel):
    risk_tolerance: RiskTolerance = RiskTolerance.MEDIUM
    investment_horizon: str = Field("short_term", regex=r'^(short_term|medium_term|long_term)$')
    priority: str = Field("normal", regex=r'^(low|normal|high|urgent)$')

class AIAnalysisJobInput(BaseModel):
    symbol: str = Field(..., regex=r'^[0-9]{4}$', description="4-digit Japanese stock code")
    symbol_name: Optional[str] = Field(None, max_length=200)
    user_id: str = Field(..., regex=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    analysis_config: Dict[str, Any]
    market_context: MarketContext
    user_preferences: UserPreferences = UserPreferences()
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "7203",
                "symbol_name": "トヨタ自動車",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "analysis_config": {
                    "types": ["technical", "sentiment"],
                    "models": [
                        {
                            "provider": "openai/gpt-4-turbo-preview",
                            "analysis_type": "technical"
                        }
                    ]
                },
                "market_context": {
                    "timeframes": ["1h", "4h"],
                    "include_chart": True
                }
            }
        }
```

## Processing Workflow

### State Machine Definition
```
queued → data_fetching → chart_generation → ai_processing → result_aggregation → completed
   ↓           ↓              ↓               ↓               ↓
 failed ←── failed ←────── failed ←────── failed ←────── failed
```

### Detailed Processing Steps

#### 1. Job Initialization (queued → data_fetching)
```python
async def initialize_job(job_input: AIAnalysisJobInput) -> JobContext:
    """ジョブ初期化とコンテキスト作成"""
    
    # ユーザークォータチェック
    quota_ok = await check_user_quota(job_input.user_id)
    if not quota_ok:
        raise QuotaExceededError("AI analysis quota exceeded")
    
    # ジョブコンテキスト作成
    context = JobContext(
        job_id=str(uuid.uuid4()),
        user_id=job_input.user_id,
        symbol=job_input.symbol,
        status=JobStatus.DATA_FETCHING,
        started_at=datetime.utcnow(),
        config=job_input
    )
    
    # Redis/DBに初期状態保存
    await save_job_context(context)
    return context
```

#### 2. Market Data Collection (data_fetching)
```python
async def fetch_market_data(context: JobContext) -> MarketData:
    """市場データ収集"""
    
    try:
        # yfinanceから価格データ取得
        stock_data = await fetch_stock_data(
            symbol=f"{context.symbol}.T",  # 東証コード変換
            timeframes=context.config.market_context.timeframes,
            history_days=30  # 30日分のデータ
        )
        
        # テクニカル指標計算
        indicators = await calculate_technical_indicators(stock_data)
        
        # ニュースデータ取得 (センチメント分析用)
        news_data = await fetch_news_data(context.symbol) if "sentiment" in context.config.analysis_config.types else None
        
        market_data = MarketData(
            symbol=context.symbol,
            price_data=stock_data,
            technical_indicators=indicators,
            news_data=news_data,
            fetched_at=datetime.utcnow()
        )
        
        # 状態更新
        await update_job_status(context.job_id, JobStatus.CHART_GENERATION)
        return market_data
        
    except Exception as e:
        await update_job_status(context.job_id, JobStatus.FAILED, error=str(e))
        raise DataFetchError(f"Market data fetch failed: {e}")
```

#### 3. Chart Generation (chart_generation)
```python
async def generate_analysis_charts(context: JobContext, market_data: MarketData) -> List[ChartImage]:
    """分析用チャート画像生成"""
    
    charts = []
    
    try:
        for timeframe in context.config.market_context.timeframes:
            # matplotlib + mplfinanceでチャート生成
            chart_buffer = await generate_candlestick_chart(
                data=market_data.price_data[timeframe],
                indicators=market_data.technical_indicators[timeframe],
                config=context.config.market_context.chart_config,
                title=f"{context.symbol} - {timeframe}"
            )
            
            # 画像をBase64エンコード
            chart_base64 = base64.b64encode(chart_buffer.getvalue()).decode()
            
            # S3/Cloudinaryにアップロード (オプション)
            chart_url = await upload_chart_image(chart_base64, 
                f"{context.job_id}_{timeframe}.png") if UPLOAD_CHARTS else None
            
            charts.append(ChartImage(
                timeframe=timeframe,
                base64_data=chart_base64,
                url=chart_url,
                generated_at=datetime.utcnow()
            ))
        
        await update_job_status(context.job_id, JobStatus.AI_PROCESSING)
        return charts
        
    except Exception as e:
        await update_job_status(context.job_id, JobStatus.FAILED, error=str(e))
        raise ChartGenerationError(f"Chart generation failed: {e}")
```

#### 4. AI Analysis Execution (ai_processing)
```python
async def execute_ai_analysis(
    context: JobContext, 
    market_data: MarketData, 
    charts: List[ChartImage]
) -> List[AIModelResult]:
    """複数AIモデルで並列分析実行"""
    
    results = []
    
    try:
        # モデル別タスク作成
        analysis_tasks = []
        for model_config in context.config.analysis_config.models:
            task = analyze_with_single_model(
                model_config=model_config,
                context=context,
                market_data=market_data,
                charts=charts
            )
            analysis_tasks.append(task)
        
        # 並列実行 (semaphoreで同時実行数制限)
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_AI_REQUESTS)
        
        async def limited_analysis(task):
            async with semaphore:
                return await task
        
        # 全てのAI分析を並列実行
        analysis_results = await asyncio.gather(
            *[limited_analysis(task) for task in analysis_tasks],
            return_exceptions=True
        )
        
        # 結果を検証・正常化
        for i, result in enumerate(analysis_results):
            if isinstance(result, Exception):
                logger.error(f"AI analysis failed for model {i}: {result}")
                # フォールバックモデルで再試行
                fallback_result = await execute_fallback_analysis(
                    context.config.analysis_config.models[i], context, market_data, charts
                )
                if fallback_result:
                    results.append(fallback_result)
            else:
                results.append(result)
        
        if not results:
            raise AIAnalysisError("All AI models failed to provide analysis")
            
        await update_job_status(context.job_id, JobStatus.RESULT_AGGREGATION)
        return results
        
    except Exception as e:
        await update_job_status(context.job_id, JobStatus.FAILED, error=str(e))
        raise
```

#### 5. Individual Model Analysis
```python
async def analyze_with_single_model(
    model_config: ModelConfig,
    context: JobContext,
    market_data: MarketData,
    charts: List[ChartImage]
) -> AIModelResult:
    """単一AIモデルでの分析実行"""
    
    start_time = time.time()
    
    try:
        # プロンプト作成
        prompt = await build_analysis_prompt(
            analysis_type=model_config.analysis_type,
            symbol=context.symbol,
            market_data=market_data,
            user_preferences=context.config.user_preferences
        )
        
        # OpenRouter API呼び出し
        openrouter_request = {
            "model": model_config.provider,
            "messages": [
                {"role": "system", "content": get_system_prompt(model_config.analysis_type)},
                {"role": "user", "content": prompt}
            ],
            "temperature": model_config.temperature,
            "max_tokens": model_config.max_tokens or 1000
        }
        
        # 画像データ追加 (Vision対応モデルの場合)
        if model_config.analysis_type == AnalysisType.TECHNICAL and charts:
            chart_content = []
            for chart in charts[:2]:  # 最大2枚まで
                chart_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{chart.base64_data}"}
                })
            
            openrouter_request["messages"][-1]["content"] = [
                {"type": "text", "text": prompt},
                *chart_content
            ]
        
        # OpenRouter API実行
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": APP_URL,
                    "X-Title": "Kaboom Stock Trading AI"
                },
                json=openrouter_request
            ) as response:
                
                if response.status == 429:
                    # レート制限エラー
                    retry_after = int(response.headers.get("retry-after", "60"))
                    await asyncio.sleep(retry_after)
                    return await analyze_with_single_model(model_config, context, market_data, charts)
                
                if response.status >= 400:
                    error_data = await response.json()
                    raise OpenRouterAPIError(f"API error {response.status}: {error_data}")
                
                response_data = await response.json()
        
        # レスポンス解析
        ai_response = response_data["choices"][0]["message"]["content"]
        parsed_result = parse_ai_response(ai_response, model_config.analysis_type)
        
        # コスト計算
        usage = response_data.get("usage", {})
        cost_usd = calculate_openrouter_cost(
            model=model_config.provider,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0)
        )
        
        # 結果作成
        processing_time = time.time() - start_time
        
        result = AIModelResult(
            model=model_config.provider,
            analysis_type=model_config.analysis_type,
            decision=parsed_result["decision"],
            confidence=parsed_result["confidence"],
            reasoning=parsed_result["reasoning"],
            raw_response=ai_response,
            cost_usd=cost_usd,
            processing_time=processing_time,
            timestamp=datetime.utcnow()
        )
        
        # 使用量トラッキング
        await track_ai_usage(context.user_id, model_config.provider, cost_usd, usage.get("total_tokens", 0))
        
        return result
        
    except Exception as e:
        logger.error(f"Single model analysis failed: {e}")
        raise AIModelError(f"Analysis failed for {model_config.provider}: {e}")
```

#### 6. Result Aggregation (result_aggregation)
```python
async def aggregate_analysis_results(
    context: JobContext,
    model_results: List[AIModelResult]
) -> AggregatedResult:
    """複数AIモデルの結果を統合"""
    
    try:
        # 決定の集約
        decisions = [result.decision for result in model_results]
        decision_counts = Counter(decisions)
        
        # 多数決による最終決定
        final_decision = decision_counts.most_common(1)[0][0]
        
        # 合意度計算
        agreement_ratio = decision_counts[final_decision] / len(decisions)
        
        # 信頼度の加重平均
        total_confidence = sum(result.confidence for result in model_results)
        consensus_confidence = total_confidence / len(model_results)
        
        # コスト合計
        total_cost = sum(result.cost_usd for result in model_results)
        
        # 実行メトリクス
        execution_metrics = ExecutionMetrics(
            total_cost_usd=total_cost,
            processing_time_seconds=sum(result.processing_time for result in model_results),
            models_used=len(model_results),
            fallback_count=len([r for r in model_results if r.is_fallback]) if hasattr(AIModelResult, 'is_fallback') else 0
        )
        
        aggregated_result = AggregatedResult(
            job_id=context.job_id,
            final_decision=final_decision,
            consensus_confidence=consensus_confidence,
            model_agreement=agreement_ratio,
            model_results=model_results,
            execution_metrics=execution_metrics,
            aggregated_at=datetime.utcnow()
        )
        
        # データベースに保存
        await save_analysis_result(aggregated_result)
        
        # WebSocket通知
        await notify_analysis_complete(context.user_id, aggregated_result)
        
        await update_job_status(context.job_id, JobStatus.COMPLETED)
        return aggregated_result
        
    except Exception as e:
        await update_job_status(context.job_id, JobStatus.FAILED, error=str(e))
        raise ResultAggregationError(f"Result aggregation failed: {e}")
```

## Output Schema

### Success Response
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "symbol": "7203",
  "symbol_name": "トヨタ自動車",
  "analysis_summary": {
    "final_decision": "buy",
    "consensus_confidence": 0.78,
    "model_agreement": 0.67,
    "key_factors": [
      "RSI oversold conditions",
      "Positive earnings sentiment", 
      "Low portfolio correlation risk"
    ]
  },
  "model_results": [
    {
      "model": "openai/gpt-4-turbo-preview",
      "analysis_type": "technical",
      "decision": "buy",
      "confidence": 0.85,
      "reasoning": "RSI at 28 indicates oversold conditions. MACD showing bullish crossover with strong volume confirmation.",
      "key_indicators": {
        "RSI": 28.5,
        "MACD": {"signal": "bullish", "strength": 0.73},
        "volume_confirmation": true
      },
      "cost_usd": 0.023,
      "processing_time": 2.34
    },
    {
      "model": "anthropic/claude-3-sonnet",
      "analysis_type": "sentiment",
      "decision": "buy", 
      "confidence": 0.72,
      "reasoning": "Recent quarterly earnings exceeded expectations. Management guidance positive for next quarter. Media sentiment largely optimistic.",
      "sentiment_factors": {
        "earnings_sentiment": "positive",
        "media_sentiment": 0.65,
        "analyst_ratings": "upgrade_trend"
      },
      "cost_usd": 0.018,
      "processing_time": 1.89
    },
    {
      "model": "google/gemini-pro-vision",
      "analysis_type": "risk",
      "decision": "hold",
      "confidence": 0.68,
      "reasoning": "Moderate portfolio concentration risk. Current market volatility elevated. Consider position sizing.",
      "risk_assessment": {
        "volatility_percentile": 75,
        "correlation_risk": "medium",
        "sector_concentration": 0.23
      },
      "cost_usd": 0.008,
      "processing_time": 3.12
    }
  ],
  "execution_metrics": {
    "total_cost_usd": 0.049,
    "total_processing_time": 7.35,
    "models_used": 3,
    "chart_images_generated": 3,
    "fallback_count": 0
  },
  "market_context": {
    "analysis_timestamp": "2024-01-15T14:30:00Z",
    "market_session": "regular",
    "current_price": 2650.0,
    "price_change": "+25.0 (+0.95%)"
  },
  "created_at": "2024-01-15T14:25:00Z",
  "completed_at": "2024-01-15T14:30:12Z"
}
```

### Error Response
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error": {
    "code": "OPENROUTER_RATE_LIMIT",
    "message": "OpenRouter API rate limit exceeded",
    "details": {
      "retry_after": 45,
      "quota_reset": "2024-01-15T15:00:00Z"
    }
  },
  "partial_results": [
    {
      "model": "openai/gpt-4-turbo-preview",
      "status": "completed",
      "decision": "buy",
      "confidence": 0.85
    },
    {
      "model": "anthropic/claude-3-sonnet", 
      "status": "failed",
      "error": "Rate limit exceeded"
    }
  ],
  "created_at": "2024-01-15T14:25:00Z",
  "failed_at": "2024-01-15T14:27:30Z"
}
```

## Idempotency Strategy

### Natural Key Definition
```python
def generate_idempotency_key(job_input: AIAnalysisJobInput) -> str:
    """冪等性キー生成"""
    
    # モデル設定のハッシュ化
    models_hash = hashlib.md5(
        json.dumps(job_input.analysis_config.models, sort_keys=True).encode()
    ).hexdigest()[:8]
    
    # 日付（時間レベルで区切り）
    analysis_date = datetime.utcnow().strftime("%Y%m%d%H")
    
    # 自然キー構成
    natural_key = f"{job_input.symbol}:{models_hash}:{analysis_date}"
    
    return natural_key

async def check_existing_analysis(idempotency_key: str) -> Optional[AggregatedResult]:
    """既存分析の確認"""
    
    # Redis cache check (1時間TTL)
    cached_result = await redis_client.get(f"ai_analysis:{idempotency_key}")
    if cached_result:
        return AggregatedResult.parse_raw(cached_result)
    
    # Database check
    existing = await db.execute(
        "SELECT * FROM ai_analysis_results WHERE idempotency_key = $1 AND created_at > NOW() - INTERVAL '1 hour'",
        idempotency_key
    )
    
    if existing:
        result = AggregatedResult.from_db_row(existing)
        # Cache for next time
        await redis_client.setex(
            f"ai_analysis:{idempotency_key}",
            3600,  # 1 hour
            result.json()
        )
        return result
    
    return None
```

## SLA & Performance Targets

### Service Level Objectives
| メトリック | 目標値 | 測定方法 |
|-----------|--------|---------|
| **Processing Time** | P95 < 90秒 | job完了までの時間 |
| **Success Rate** | > 95% | 正常完了/全実行 |
| **API Cost** | < $0.10/分析 | OpenRouter課金額 |
| **Availability** | > 99% | サービス稼働率 |

### Performance Optimizations

#### 1. Parallel Processing
```python
# モデル並列実行
MAX_CONCURRENT_AI_REQUESTS = 3
SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_AI_REQUESTS)

# タイムアウト設定
ANALYSIS_TIMEOUT = 180  # 3分
```

#### 2. Caching Strategy
```python
# 市場データキャッシュ (5分)
MARKET_DATA_CACHE_TTL = 300

# チャート画像キャッシュ (15分)  
CHART_CACHE_TTL = 900

# AI分析結果キャッシュ (1時間)
AI_ANALYSIS_CACHE_TTL = 3600
```

#### 3. Resource Management
```python
# メモリ使用量制限
MAX_CHART_SIZE = 5 * 1024 * 1024  # 5MB per chart
MAX_CONCURRENT_CHARTS = 5

# AI API制限
OPENROUTER_RATE_LIMIT = 100  # requests per minute
```

## Error Handling & Recovery

### Retry Strategy
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((OpenRouterRateLimitError, ConnectionError))
)
async def call_openrouter_with_retry(request: dict) -> dict:
    """OpenRouter API呼び出し（リトライ付き）"""
    # 実装は前述のanalyze_with_single_model参照
    pass
```

### Fallback Models
```python
FALLBACK_CONFIG = {
    "openai/gpt-4-turbo-preview": "openai/gpt-3.5-turbo",
    "anthropic/claude-3-sonnet": "openai/gpt-3.5-turbo", 
    "google/gemini-pro-vision": "meta-llama/llama-2-70b-chat"
}

async def execute_fallback_analysis(failed_config: ModelConfig, ...) -> Optional[AIModelResult]:
    """フォールバックモデルでの分析実行"""
    
    fallback_model = FALLBACK_CONFIG.get(failed_config.provider)
    if not fallback_model:
        return None
    
    fallback_config = ModelConfig(
        provider=fallback_model,
        analysis_type=failed_config.analysis_type,
        temperature=failed_config.temperature
    )
    
    try:
        result = await analyze_with_single_model(fallback_config, context, market_data, charts)
        result.is_fallback = True  # フォールバックフラグ
        return result
    except Exception:
        return None
```

## Monitoring & Observability

### Key Metrics
```python
from prometheus_client import Counter, Histogram, Gauge

# 実行メトリクス
ai_analysis_requests_total = Counter('ai_analysis_requests_total', 'AI analysis requests', ['status', 'user_tier'])
ai_analysis_duration = Histogram('ai_analysis_duration_seconds', 'AI analysis duration', ['model'])
ai_analysis_cost = Histogram('ai_analysis_cost_usd', 'AI analysis cost', ['model', 'analysis_type'])

# キューメトリクス
ai_analysis_queue_size = Gauge('ai_analysis_queue_size', 'Pending AI analysis jobs')
ai_analysis_active = Gauge('ai_analysis_active', 'Active AI analysis jobs')

# エラーメトリクス
ai_analysis_errors_total = Counter('ai_analysis_errors_total', 'AI analysis errors', ['error_type', 'model'])
```

### Logging Strategy
```python
import structlog

logger = structlog.get_logger()

# 構造化ログ
await logger.ainfo(
    "AI analysis started",
    job_id=context.job_id,
    user_id=context.user_id,
    symbol=context.symbol,
    models=len(context.config.analysis_config.models),
    trace_id=context.trace_id
)

await logger.ainfo(
    "AI analysis completed", 
    job_id=context.job_id,
    final_decision=result.final_decision,
    consensus_confidence=result.consensus_confidence,
    total_cost=result.execution_metrics.total_cost_usd,
    processing_time=result.execution_metrics.processing_time_seconds,
    trace_id=context.trace_id
)
```

## Integration Points

### Celery Task Definition
```python
from celery import Celery
from app.tasks.celery_app import celery_app

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=300,  # 5分でタイムアウト
    soft_time_limit=270  # 4分30秒でソフトタイムアウト
)
async def execute_ai_analysis_task(self, job_input_json: str) -> str:
    """AI分析Celeryタスク"""
    
    try:
        job_input = AIAnalysisJobInput.parse_raw(job_input_json)
        
        # 冪等性チェック
        idempotency_key = generate_idempotency_key(job_input)
        existing_result = await check_existing_analysis(idempotency_key)
        if existing_result:
            return existing_result.json()
        
        # ジョブ実行
        context = await initialize_job(job_input)
        market_data = await fetch_market_data(context)
        charts = await generate_analysis_charts(context, market_data)
        model_results = await execute_ai_analysis(context, market_data, charts)
        final_result = await aggregate_analysis_results(context, model_results)
        
        return final_result.json()
        
    except Exception as e:
        logger.error(f"AI analysis task failed: {e}", exc_info=True)
        
        # リトライ可能エラーの場合は再実行
        if isinstance(e, (OpenRouterRateLimitError, ConnectionError)):
            raise self.retry(exc=e, countdown=min(60 * (2 ** self.request.retries), 300))
        
        # 致命的エラーの場合は失敗として記録
        if hasattr(self, 'job_id'):
            await update_job_status(self.job_id, JobStatus.FAILED, error=str(e))
        
        raise
```

### API Endpoint Integration
```python
@router.post("/ai/analyze", response_model=schemas.AIAnalysisResponse)
async def submit_ai_analysis(
    request: schemas.AIAnalysisRequest,
    current_user: models.User = Depends(get_current_user)
) -> schemas.AIAnalysisResponse:
    """AI分析ジョブ投入エンドポイント"""
    
    # ユーザークォータチェック
    quota_available = await check_user_ai_quota(current_user.id)
    if not quota_available:
        raise HTTPException(
            status_code=429,
            detail="AI analysis quota exceeded for current period"
        )
    
    # ジョブ入力作成
    job_input = AIAnalysisJobInput(
        symbol=request.symbol,
        symbol_name=request.symbol_name,
        user_id=str(current_user.id),
        analysis_config=request.analysis_config,
        market_context=request.market_context,
        user_preferences=request.user_preferences
    )
    
    # 冪等性チェック
    idempotency_key = generate_idempotency_key(job_input)
    existing_result = await check_existing_analysis(idempotency_key)
    if existing_result:
        return schemas.AIAnalysisResponse(
            job_id=existing_result.job_id,
            status="completed",
            result=existing_result
        )
    
    # Celeryタスク投入
    task = execute_ai_analysis_task.delay(job_input.json())
    
    # 応答作成
    return schemas.AIAnalysisResponse(
        job_id=task.id,
        status="queued",
        estimated_completion=datetime.utcnow() + timedelta(minutes=2)
    )
```

## Testing Strategy

### Unit Tests
```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_ai_analysis_success():
    """正常系テスト"""
    
    # Mock設定
    mock_market_data = MarketData(...)
    mock_charts = [ChartImage(...)]
    mock_ai_results = [AIModelResult(...)]
    
    with patch('app.services.ai_analysis.fetch_market_data', return_value=mock_market_data):
        with patch('app.services.ai_analysis.generate_analysis_charts', return_value=mock_charts):
            with patch('app.services.ai_analysis.execute_ai_analysis', return_value=mock_ai_results):
                
                job_input = AIAnalysisJobInput(...)
                result = await execute_ai_analysis_workflow(job_input)
                
                assert result.final_decision in ['buy', 'sell', 'hold']
                assert 0 <= result.consensus_confidence <= 1
                assert result.execution_metrics.total_cost_usd > 0

@pytest.mark.asyncio 
async def test_openrouter_rate_limit_handling():
    """レート制限エラーのテスト"""
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {"retry-after": "60"}
        mock_post.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(OpenRouterRateLimitError):
            await analyze_with_single_model(...)
```

### Integration Tests
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_ai_analysis_pipeline():
    """E2E統合テスト"""
    
    # 実際のOpenRouter APIを使用（テスト用API KEY）
    job_input = AIAnalysisJobInput(
        symbol="7203",
        user_id="test-user-id",
        analysis_config={
            "types": ["technical"],
            "models": [{"provider": "openai/gpt-3.5-turbo", "analysis_type": "technical"}]
        },
        market_context=MarketContext(timeframes=["1d"])
    )
    
    result = await execute_ai_analysis_workflow(job_input)
    
    assert result.status == JobStatus.COMPLETED
    assert len(result.model_results) == 1
    assert result.execution_metrics.total_cost_usd < 0.05  # コスト制限
```

## 関連文書

- [OpenRouter統合設計書](../../ai/openrouter-integration.md)
- [データベース設計書](../../data/schema.md)
- [エラーカタログ](../../api/error-catalog.md)
- [API開発計画書](../../api-development-plan.md)
- [ADR-0001: OpenRouter採用理由](../../architecture/adr/0001-openrouter-ai-integration.md)