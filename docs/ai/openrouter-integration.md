# OpenRouter統合設計書

## Overview

Kaboom株式自動売買システムにおけるOpenRouter統合の詳細設計書です。
複数AIモデルの統一管理、コスト最適化、エラーハンドリング戦略を定義します。

## 基本設定

### 接続設定

```python
OPENROUTER_CONFIG = {
    # 基本接続設定
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": "${OPENROUTER_API_KEY}",  # 環境変数から取得
    "timeout": 30,  # 30秒タイムアウト
    "max_retries": 3,
    
    # Headers設定
    "default_headers": {
        "HTTP-Referer": "https://kaboom-trading.com",
        "X-Title": "Kaboom Stock Trading AI"
    },
    
    # レート制限設定
    "rate_limit": {
        "requests_per_minute": 100,
        "concurrent_requests": 10,
        "backoff_factor": 2.0
    }
}
```

### 環境変数

```bash
# 必須
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx

# オプション（デバッグ・監視用）
OPENROUTER_DEBUG=false
OPENROUTER_LOG_REQUESTS=true
OPENROUTER_COST_TRACKING=true
```

## モデル設定戦略

### 用途別モデル配置

```python
AI_MODEL_CONFIG = {
    # テクニカル分析：精密な数値分析が得意
    "technical_analysis": {
        "primary": "openai/gpt-4-turbo-preview",
        "fallback": "anthropic/claude-3-sonnet",
        "temperature": 0.1,
        "max_tokens": 1000
    },
    
    # センチメント分析：自然言語理解が重要
    "sentiment_analysis": {
        "primary": "anthropic/claude-3-sonnet", 
        "fallback": "openai/gpt-4-turbo-preview",
        "temperature": 0.2,
        "max_tokens": 800
    },
    
    # リスク評価：論理的推論が重要
    "risk_assessment": {
        "primary": "google/gemini-pro-vision",
        "fallback": "openai/gpt-4-turbo-preview", 
        "temperature": 0.1,
        "max_tokens": 1200
    },
    
    # 汎用分析：コストパフォーマンス重視
    "general_analysis": {
        "primary": "meta-llama/llama-2-70b-chat",
        "fallback": "openai/gpt-3.5-turbo",
        "temperature": 0.15,
        "max_tokens": 800
    }
}
```

### モデル性能・コスト比較マトリックス

| モデル | 用途適性 | 応答時間 | コスト(/1K tokens) | 精度 | 推奨用途 |
|--------|----------|----------|-------------------|------|----------|
| `openai/gpt-4-turbo-preview` | ★★★★★ | 2-4s | $0.01 | 95% | テクニカル分析 |
| `anthropic/claude-3-sonnet` | ★★★★☆ | 3-5s | $0.003 | 92% | センチメント分析 |
| `google/gemini-pro-vision` | ★★★★☆ | 2-3s | $0.0005 | 90% | チャート画像分析 |
| `meta-llama/llama-2-70b-chat` | ★★★☆☆ | 4-6s | $0.0004 | 85% | 汎用分析 |
| `openai/gpt-3.5-turbo` | ★★☆☆☆ | 1-2s | $0.0015 | 80% | 簡易分析・フォールバック |

## API統合実装

### 基本クライアント実装

```python
# app/external/openrouter_client.py

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from app.config.settings import settings

logger = logging.getLogger(__name__)

class AIAnalysisType(str, Enum):
    TECHNICAL = "technical"
    SENTIMENT = "sentiment" 
    RISK = "risk"
    GENERAL = "general"

@dataclass
class AIRequest:
    analysis_type: AIAnalysisType
    symbol: str
    prompt: str
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    image_data: Optional[str] = None  # Base64エンコード画像

@dataclass  
class AIResponse:
    model: str
    decision: str  # buy, sell, hold
    confidence: float
    reasoning: str
    cost_usd: float
    processing_time: float
    request_id: str

class OpenRouterClient:
    def __init__(self):
        self.base_url = settings.OPENROUTER_BASE_URL
        self.api_key = settings.OPENROUTER_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": settings.APP_URL,
                "X-Title": "Kaboom Stock Trading AI"
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def analyze_stock(self, request: AIRequest) -> AIResponse:
        """株式分析APIの呼び出し"""
        model = request.model or self._get_default_model(request.analysis_type)
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system", 
                    "content": self._get_system_prompt(request.analysis_type)
                },
                {
                    "role": "user",
                    "content": request.prompt
                }
            ],
            "temperature": request.temperature or self._get_default_temperature(request.analysis_type),
            "max_tokens": request.max_tokens or self._get_default_max_tokens(request.analysis_type)
        }
        
        # 画像データがある場合（チャート分析）
        if request.image_data:
            payload["messages"][-1]["content"] = [
                {"type": "text", "text": request.prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{request.image_data}"}}
            ]
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload
            ) as response:
                
                if response.status == 429:
                    # レート制限エラー
                    retry_after = int(response.headers.get("retry-after", "60"))
                    raise OpenRouterRateLimitError(f"Rate limit exceeded, retry after {retry_after}s")
                    
                if response.status >= 400:
                    error_data = await response.json()
                    raise OpenRouterAPIError(f"API error: {error_data}")
                    
                data = await response.json()
                processing_time = asyncio.get_event_loop().time() - start_time
                
                # レスポンス解析
                content = data["choices"][0]["message"]["content"]
                parsed_response = self._parse_ai_response(content, request.analysis_type)
                
                return AIResponse(
                    model=model,
                    decision=parsed_response["decision"],
                    confidence=parsed_response["confidence"],
                    reasoning=parsed_response["reasoning"],
                    cost_usd=self._calculate_cost(data["usage"], model),
                    processing_time=processing_time,
                    request_id=data.get("id", "")
                )
                
        except asyncio.TimeoutError:
            raise OpenRouterTimeoutError("Request timeout")
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            raise
    
    async def batch_analyze(self, requests: List[AIRequest]) -> List[AIResponse]:
        """複数分析の並列実行"""
        semaphore = asyncio.Semaphore(settings.OPENROUTER_CONCURRENT_REQUESTS)
        
        async def _analyze_with_semaphore(req: AIRequest) -> AIResponse:
            async with semaphore:
                return await self.analyze_stock(req)
        
        tasks = [_analyze_with_semaphore(req) for req in requests]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def _get_default_model(self, analysis_type: AIAnalysisType) -> str:
        return AI_MODEL_CONFIG[analysis_type.value]["primary"]
    
    def _get_default_temperature(self, analysis_type: AIAnalysisType) -> float:
        return AI_MODEL_CONFIG[analysis_type.value]["temperature"]
        
    def _get_default_max_tokens(self, analysis_type: AIAnalysisType) -> int:
        return AI_MODEL_CONFIG[analysis_type.value]["max_tokens"]
    
    def _get_system_prompt(self, analysis_type: AIAnalysisType) -> str:
        """分析タイプ別のシステムプロンプト取得"""
        prompts = {
            AIAnalysisType.TECHNICAL: TECHNICAL_ANALYSIS_PROMPT,
            AIAnalysisType.SENTIMENT: SENTIMENT_ANALYSIS_PROMPT,
            AIAnalysisType.RISK: RISK_ASSESSMENT_PROMPT,
            AIAnalysisType.GENERAL: GENERAL_ANALYSIS_PROMPT
        }
        return prompts[analysis_type]
    
    def _parse_ai_response(self, content: str, analysis_type: AIAnalysisType) -> Dict[str, Any]:
        """AI応答の標準化解析"""
        try:
            # JSON形式での構造化レスポンスを期待
            import json
            parsed = json.loads(content)
            
            return {
                "decision": parsed.get("decision", "hold").lower(),
                "confidence": float(parsed.get("confidence", 0.5)),
                "reasoning": parsed.get("reasoning", "No reasoning provided")
            }
        except json.JSONDecodeError:
            # フォールバック：テキスト解析
            return self._fallback_text_parse(content)
    
    def _fallback_text_parse(self, content: str) -> Dict[str, Any]:
        """テキストからの判断抽出"""
        content_lower = content.lower()
        
        if "buy" in content_lower or "購入" in content_lower:
            decision = "buy"
        elif "sell" in content_lower or "売却" in content_lower:
            decision = "sell"
        else:
            decision = "hold"
            
        # 簡易的な信頼度推定
        confidence_keywords = ["confident", "certain", "likely", "probable"]
        confidence = 0.7 if any(kw in content_lower for kw in confidence_keywords) else 0.5
        
        return {
            "decision": decision,
            "confidence": confidence,
            "reasoning": content[:500]  # 最初の500文字
        }
    
    def _calculate_cost(self, usage: Dict, model: str) -> float:
        """使用トークン数からコスト計算"""
        # OpenRouterの料金体系に基づく
        PRICING = {
            "openai/gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
            "anthropic/claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "google/gemini-pro-vision": {"input": 0.0005, "output": 0.0015},
            "meta-llama/llama-2-70b-chat": {"input": 0.0004, "output": 0.0008}
        }
        
        if model not in PRICING:
            return 0.0
            
        input_cost = (usage.get("prompt_tokens", 0) / 1000) * PRICING[model]["input"]
        output_cost = (usage.get("completion_tokens", 0) / 1000) * PRICING[model]["output"]
        
        return round(input_cost + output_cost, 6)

# 例外クラス定義
class OpenRouterError(Exception):
    pass

class OpenRouterAPIError(OpenRouterError):
    pass

class OpenRouterRateLimitError(OpenRouterError):
    pass
    
class OpenRouterTimeoutError(OpenRouterError):
    pass
```

## プロンプトテンプレート

### テクニカル分析プロンプト

```python
TECHNICAL_ANALYSIS_PROMPT = """
あなたは経験豊富な株式テクニカルアナリストです。

提供される情報:
- 銘柄コード・銘柄名
- 現在価格・前日比
- テクニカル指標 (RSI, MACD, ボリンジャーバンド等)
- チャート画像 (提供される場合)

分析要件:
1. テクニカル指標の総合的解釈
2. トレンド・サポート/レジスタンス分析
3. 売買タイミングの判断
4. リスク要因の特定

レスポンス形式 (必須JSON):
{
  "decision": "buy|sell|hold",
  "confidence": 0.0-1.0,
  "reasoning": "詳細な分析理由 (200文字以内)",
  "key_indicators": ["指標名1", "指標名2"],
  "price_target": 数値 (optional),
  "risk_factors": ["リスク要因1", "リスク要因2"]
}

注意事項:
- 過度に楽観的/悲観的な判断は避ける
- 複数指標の合意を重視
- 不確実性は confidence に反映
"""

SENTIMENT_ANALYSIS_PROMPT = """
あなたは市場センチメント分析の専門家です。

提供される情報:
- 銘柄に関連するニュース記事
- SNS投稿・掲示板コメント
- 決算情報・企業発表
- 市場全体の動向

分析要件:
1. 短期・中期のセンチメント方向
2. 材料の重要度・市場への影響度
3. センチメント変化の持続性
4. ネガティブ要因の評価

レスポンス形式 (必須JSON):
{
  "decision": "buy|sell|hold",
  "confidence": 0.0-1.0,
  "reasoning": "センチメント分析の根拠 (200文字以内)",
  "sentiment_score": -1.0-1.0,
  "key_factors": ["要因1", "要因2"],
  "duration_estimate": "short|medium|long"
}
"""

RISK_ASSESSMENT_PROMPT = """
あなたはリスク管理の専門家です。

提供される情報:
- 現在のポートフォリオ構成
- 銘柄の過去ボラティリティ
- 市場環境・マクロ要因
- 相関関係分析

分析要件:
1. 個別銘柄リスクの評価
2. ポートフォリオ全体への影響
3. 最大損失の可能性 (VaR推定)
4. リスク軽減策の提案

レスポンス形式 (必須JSON):
{
  "decision": "buy|sell|hold",
  "confidence": 0.0-1.0,
  "reasoning": "リスク評価の根拠 (200文字以内)",
  "risk_level": "low|medium|high",
  "max_loss_estimate": 数値 (percentage),
  "risk_factors": ["要因1", "要因2"],
  "mitigation_suggestions": ["対策1", "対策2"]
}
"""
```

## エラーハンドリング・フォールバック戦略

### 段階的フォールバック

```python
class AIAnalysisService:
    async def analyze_with_fallback(self, request: AIRequest) -> AIResponse:
        models = [
            AI_MODEL_CONFIG[request.analysis_type.value]["primary"],
            AI_MODEL_CONFIG[request.analysis_type.value]["fallback"],
            "openai/gpt-3.5-turbo"  # 最終フォールバック
        ]
        
        for i, model in enumerate(models):
            try:
                request.model = model
                response = await self.openrouter_client.analyze_stock(request)
                
                # 成功時は追加メタデータを記録
                response.fallback_level = i
                return response
                
            except OpenRouterRateLimitError:
                if i < len(models) - 1:
                    logger.warning(f"Rate limit for {model}, trying fallback")
                    continue
                raise
                
            except OpenRouterAPIError as e:
                if i < len(models) - 1:
                    logger.warning(f"API error for {model}: {e}, trying fallback")
                    continue
                raise
                
            except Exception as e:
                if i < len(models) - 1:
                    logger.error(f"Unexpected error for {model}: {e}, trying fallback")
                    continue
                raise
        
        raise Exception("All AI models failed")
```

## コスト管理・最適化

### 使用量監視

```python
class AIUsageTracker:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def track_usage(self, user_id: str, model: str, cost: float, tokens: int):
        """使用量トラッキング"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 日次使用量
        await self.redis.hincrby(f"ai_usage:daily:{today}", f"user:{user_id}", tokens)
        await self.redis.hincrbyfloat(f"ai_usage:cost_daily:{today}", f"user:{user_id}", cost)
        
        # モデル別使用量
        await self.redis.hincrby(f"ai_usage:model:{model}:{today}", "requests", 1)
        await self.redis.hincrbyfloat(f"ai_usage:model:{model}:{today}", "cost", cost)
    
    async def check_user_quota(self, user_id: str, user_tier: str) -> bool:
        """ユーザークォータチェック"""
        quotas = {
            "basic": {"daily_requests": 10, "monthly_cost": 5.0},
            "premium": {"daily_requests": 100, "monthly_cost": 50.0},
            "enterprise": {"daily_requests": 1000, "monthly_cost": 500.0}
        }
        
        if user_tier not in quotas:
            return False
            
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        
        daily_requests = await self.redis.hget(f"ai_usage:daily:{today}", f"user:{user_id}") or 0
        monthly_cost = await self.redis.hget(f"ai_usage:cost_monthly:{month}", f"user:{user_id}") or 0.0
        
        quota = quotas[user_tier]
        return (int(daily_requests) < quota["daily_requests"] and 
                float(monthly_cost) < quota["monthly_cost"])
```

### コスト最適化戦略

```python
class CostOptimizer:
    """AIコスト最適化"""
    
    def optimize_model_selection(self, analysis_type: AIAnalysisType, 
                                 user_tier: str, urgency: str) -> str:
        """コスト効率を考慮したモデル選択"""
        
        if user_tier == "basic":
            # 基本ユーザーはコスト重視
            if urgency == "low":
                return "meta-llama/llama-2-70b-chat"
            else:
                return "openai/gpt-3.5-turbo"
                
        elif user_tier == "premium":
            # プレミアムは品質・コストバランス
            return AI_MODEL_CONFIG[analysis_type.value]["primary"]
            
        else:  # enterprise
            # エンタープライズは品質優先
            return "openai/gpt-4-turbo-preview"
    
    def adjust_parameters(self, base_request: AIRequest, cost_limit: float) -> AIRequest:
        """コスト制限に応じたパラメータ調整"""
        if cost_limit < 0.01:  # 低コスト要求
            base_request.max_tokens = min(base_request.max_tokens or 800, 500)
            base_request.temperature = 0.1  # 決定論的で短い応答
            
        return base_request
```

## 監視・アラート

### メトリクス定義

```python
# Prometheus metrics
openrouter_requests_total = Counter(
    'openrouter_requests_total',
    'Total OpenRouter API requests',
    ['model', 'analysis_type', 'status']
)

openrouter_cost_usd = Histogram(
    'openrouter_cost_usd',
    'OpenRouter request cost in USD',
    ['model', 'user_tier']
)

openrouter_response_time = Histogram(
    'openrouter_response_time_seconds',
    'OpenRouter API response time',
    ['model']
)

ai_analysis_accuracy = Gauge(
    'ai_analysis_accuracy',
    'AI analysis accuracy score',
    ['model', 'analysis_type']
)
```

### ダッシュボード監視項目

1. **リアルタイム使用量**
   - 秒間リクエスト数
   - アクティブモデル数
   - 同時実行数

2. **コスト監視**
   - 日次/月次コスト
   - ユーザー別使用量
   - モデル別コスト効率

3. **品質監視**
   - レスポンス時間分布
   - エラー率
   - フォールバック発生率

4. **アラート条件**
   - 日次コスト > $100
   - エラー率 > 5%
   - 平均レスポンス時間 > 10秒

## 次のステップ

1. **基本実装** - OpenRouterクライアントライブラリ作成
2. **プロンプト最適化** - テストデータでのプロンプトチューニング
3. **パフォーマンステスト** - 負荷テスト・コスト分析
4. **監視システム構築** - メトリクス・アラート設定

## 関連ドキュメント

- [ADR-0001: OpenRouter AI統合戦略](../architecture/adr/0001-openrouter-ai-integration.md)
- [エラーカタログ](../api/error-catalog.md)
- [AI分析ジョブ仕様書](../async/job-specifications/ai-analysis-job.md) - 予定