# app/services/openrouter_client.py

import asyncio
import aiohttp
import logging
import json
import hashlib
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

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
    timestamp: datetime
    raw_response: Optional[str] = None
    fallback_level: int = 0

class OpenRouterError(Exception):
    """Base OpenRouter exception"""
    pass

class OpenRouterAPIError(OpenRouterError):
    """OpenRouter API error"""
    pass

class OpenRouterRateLimitError(OpenRouterError):
    """OpenRouter rate limit exceeded"""
    pass
    
class OpenRouterTimeoutError(OpenRouterError):
    """OpenRouter request timeout"""
    pass

# AI モデル設定 (docs/ai/openrouter-integration.md に基づく)
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
    },
    "risk_assessment": {
        "primary": "google/gemini-pro-vision",
        "fallback": "openai/gpt-4-turbo-preview", 
        "temperature": 0.1,
        "max_tokens": 1200
    },
    "general_analysis": {
        "primary": "meta-llama/llama-2-70b-chat",
        "fallback": "openai/gpt-3.5-turbo",
        "temperature": 0.15,
        "max_tokens": 800
    }
}

# プロンプトテンプレート (docs/ai/openrouter-integration.md から)
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

GENERAL_ANALYSIS_PROMPT = """
あなたは総合的な投資分析の専門家です。

提供される情報を総合的に分析し、投資判断を提供してください。

レスポンス形式 (必須JSON):
{
  "decision": "buy|sell|hold",
  "confidence": 0.0-1.0,
  "reasoning": "分析の根拠 (200文字以内)"
}
"""

class OpenRouterClient:
    def __init__(self):
        self.base_url = settings.OPENROUTER_BASE_URL
        self.api_key = settings.OPENROUTER_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
            
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=settings.AI_ANALYSIS_TIMEOUT),
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
        
        start_time = time.time()
        
        try:
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload
            ) as response:
                
                if response.status == 429:
                    # レート制限エラー
                    retry_after = int(response.headers.get("retry-after", "60"))
                    logger.warning(f"OpenRouter rate limit exceeded, retry after {retry_after}s")
                    raise OpenRouterRateLimitError(f"Rate limit exceeded, retry after {retry_after}s")
                    
                if response.status >= 400:
                    error_data = await response.json()
                    logger.error(f"OpenRouter API error {response.status}: {error_data}")
                    raise OpenRouterAPIError(f"API error {response.status}: {error_data}")
                    
                data = await response.json()
                processing_time = time.time() - start_time
                
                # レスポンス解析
                content = data["choices"][0]["message"]["content"]
                parsed_response = self._parse_ai_response(content, request.analysis_type)
                
                return AIResponse(
                    model=model,
                    decision=parsed_response["decision"],
                    confidence=parsed_response["confidence"],
                    reasoning=parsed_response["reasoning"],
                    cost_usd=self._calculate_cost(data.get("usage", {}), model),
                    processing_time=processing_time,
                    request_id=data.get("id", ""),
                    timestamp=datetime.utcnow(),
                    raw_response=content
                )
                
        except asyncio.TimeoutError:
            logger.error("OpenRouter request timeout")
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
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 例外処理
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch analysis error: {result}")
                continue
            processed_results.append(result)
            
        return processed_results
    
    def _get_default_model(self, analysis_type: AIAnalysisType) -> str:
        config_key = f"{analysis_type.value}_analysis"
        if config_key not in AI_MODEL_CONFIG:
            config_key = "general_analysis"  # フォールバック
        return AI_MODEL_CONFIG[config_key]["primary"]
    
    def _get_default_temperature(self, analysis_type: AIAnalysisType) -> float:
        config_key = f"{analysis_type.value}_analysis"
        if config_key not in AI_MODEL_CONFIG:
            config_key = "general_analysis"  # フォールバック
        return AI_MODEL_CONFIG[config_key]["temperature"]
        
    def _get_default_max_tokens(self, analysis_type: AIAnalysisType) -> int:
        config_key = f"{analysis_type.value}_analysis"
        if config_key not in AI_MODEL_CONFIG:
            config_key = "general_analysis"  # フォールバック
        return AI_MODEL_CONFIG[config_key]["max_tokens"]
    
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
        confidence_keywords = ["confident", "certain", "likely", "probable", "確信", "確実"]
        confidence = 0.7 if any(kw in content_lower for kw in confidence_keywords) else 0.5
        
        return {
            "decision": decision,
            "confidence": confidence,
            "reasoning": content[:200]  # 最初の200文字
        }
    
    def _calculate_cost(self, usage: Dict, model: str) -> float:
        """使用トークン数からコスト計算"""
        # OpenRouterの料金体系に基づく (概算)
        PRICING = {
            "openai/gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
            "anthropic/claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "google/gemini-pro-vision": {"input": 0.0005, "output": 0.0015},
            "meta-llama/llama-2-70b-chat": {"input": 0.0004, "output": 0.0008},
            "openai/gpt-3.5-turbo": {"input": 0.0015, "output": 0.002}
        }
        
        if model not in PRICING:
            return 0.0
            
        input_cost = (usage.get("prompt_tokens", 0) / 1000) * PRICING[model]["input"]
        output_cost = (usage.get("completion_tokens", 0) / 1000) * PRICING[model]["output"]
        
        return round(input_cost + output_cost, 6)

# フォールバック機能付きAI分析サービス
class AIAnalysisService:
    def __init__(self):
        self.openrouter_client = None
        
    async def __aenter__(self):
        self.openrouter_client = await OpenRouterClient().__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.openrouter_client:
            await self.openrouter_client.__aexit__(exc_type, exc_val, exc_tb)
            
    async def analyze_with_fallback(self, request: AIRequest) -> AIResponse:
        """フォールバック機能付きAI分析"""
        config_key = f"{request.analysis_type.value}_analysis"
        if config_key not in AI_MODEL_CONFIG:
            config_key = "general_analysis"  # フォールバック
        
        models = [
            AI_MODEL_CONFIG[config_key]["primary"],
            AI_MODEL_CONFIG[config_key]["fallback"],
            "openai/gpt-3.5-turbo"  # 最終フォールバック
        ]
        
        for i, model in enumerate(models):
            try:
                request.model = model
                response = await self.openrouter_client.analyze_stock(request)
                
                # フォールバックレベルを記録
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

# 使用量追跡用のユーティリティ
def generate_idempotency_key(symbol: str, analysis_config: Dict, analysis_date: str = None) -> str:
    """冪等性キー生成"""
    if analysis_date is None:
        analysis_date = datetime.utcnow().strftime("%Y%m%d%H")
    
    # モデル設定のハッシュ化
    config_hash = hashlib.md5(
        json.dumps(analysis_config, sort_keys=True).encode()
    ).hexdigest()[:8]
    
    # 自然キー構成
    natural_key = f"{symbol}:{config_hash}:{analysis_date}"
    return natural_key

# 使用例とテスト用コード
async def test_openrouter_client():
    """OpenRouterクライアントのテスト"""
    try:
        async with OpenRouterClient() as client:
            request = AIRequest(
                analysis_type=AIAnalysisType.TECHNICAL,
                symbol="7203",
                prompt="トヨタ自動車（7203）のテクニカル分析を実行してください。現在価格は2650円です。"
            )
            
            response = await client.analyze_stock(request)
            
            print(f"Decision: {response.decision}")
            print(f"Confidence: {response.confidence}")
            print(f"Reasoning: {response.reasoning}")
            print(f"Cost: ${response.cost_usd}")
            print(f"Processing time: {response.processing_time}s")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    # テスト実行
    asyncio.run(test_openrouter_client())