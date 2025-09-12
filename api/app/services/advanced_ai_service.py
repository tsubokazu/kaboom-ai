# app/services/advanced_ai_service.py

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import statistics
import json

from app.services.openrouter_client import (
    OpenRouterClient, AIRequest, AIResponse, AIAnalysisType,
    AIAnalysisService
)
from app.services.redis_client import redis_client

logger = logging.getLogger(__name__)

class ConsensusStrategy(str, Enum):
    MAJORITY = "majority"           # 過半数決
    WEIGHTED_AVERAGE = "weighted"   # 信頼度重み付け平均
    CONSERVATIVE = "conservative"   # 保守的判断（リスク重視）
    AGGRESSIVE = "aggressive"      # 積極的判断（収益重視）

@dataclass
class ModelWeight:
    """モデル別重み設定"""
    technical_weight: float = 1.0
    sentiment_weight: float = 1.0
    risk_weight: float = 1.0
    general_weight: float = 0.5

@dataclass
class ConsensusResult:
    """マルチモデル合意結果"""
    final_decision: str            # buy, sell, hold
    consensus_confidence: float    # 0.0-1.0
    reasoning: str
    individual_results: List[AIResponse]
    agreement_level: float         # モデル間合意度
    processing_time: float
    total_cost: float
    timestamp: datetime
    
    # 詳細分析結果
    technical_analysis: Optional[AIResponse] = None
    sentiment_analysis: Optional[AIResponse] = None
    risk_analysis: Optional[AIResponse] = None
    
    # 統計情報
    confidence_distribution: Dict[str, float] = None
    decision_breakdown: Dict[str, int] = None

class AdvancedAIService:
    """高度なAI分析サービス - マルチモデル合意機能"""
    
    def __init__(self, model_weights: ModelWeight = None):
        self.model_weights = model_weights or ModelWeight()
        self.ai_service = None
        
    async def __aenter__(self):
        self.ai_service = await AIAnalysisService().__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.ai_service:
            await self.ai_service.__aexit__(exc_type, exc_val, exc_tb)

    async def multi_model_consensus_analysis(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        strategy: ConsensusStrategy = ConsensusStrategy.WEIGHTED_AVERAGE,
        cache_minutes: int = 30
    ) -> ConsensusResult:
        """マルチモデル合意分析"""
        
        # キャッシュチェック
        cache_key = f"consensus_analysis:{symbol}:{strategy.value}:{datetime.utcnow().strftime('%Y%m%d%H%M')[:11]}"
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            return ConsensusResult(**json.loads(cached_result))
        
        start_time = datetime.utcnow()
        
        # 並列分析実行
        analysis_tasks = [
            self._technical_analysis(symbol, market_data),
            self._sentiment_analysis(symbol, market_data),
            self._risk_analysis(symbol, market_data)
        ]
        
        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # エラーハンドリングと結果整理
        valid_results = []
        technical_result = None
        sentiment_result = None
        risk_result = None
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Analysis {i} failed: {result}")
                continue
            valid_results.append(result)
            
            # 分析種別ごとに分類
            if result.model and "gpt-4" in result.model.lower():
                technical_result = result
            elif result.model and "claude" in result.model.lower():
                sentiment_result = result
            elif result.model and "gemini" in result.model.lower():
                risk_result = result
        
        if not valid_results:
            raise Exception("All AI analyses failed")
        
        # 合意形成処理
        consensus = await self._form_consensus(valid_results, strategy)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 結果構築
        result = ConsensusResult(
            final_decision=consensus["decision"],
            consensus_confidence=consensus["confidence"],
            reasoning=consensus["reasoning"],
            individual_results=valid_results,
            agreement_level=consensus["agreement"],
            processing_time=processing_time,
            total_cost=sum(r.cost_usd for r in valid_results),
            timestamp=datetime.utcnow(),
            technical_analysis=technical_result,
            sentiment_analysis=sentiment_result,
            risk_analysis=risk_result,
            confidence_distribution=consensus["confidence_dist"],
            decision_breakdown=consensus["decision_breakdown"]
        )
        
        # 結果をキャッシュ
        await redis_client.set(
            cache_key, 
            json.dumps(result.__dict__, default=str),
            expire=cache_minutes * 60
        )
        
        # WebSocket配信
        await self._broadcast_consensus_result(symbol, result)
        
        return result

    async def _technical_analysis(self, symbol: str, market_data: Dict) -> AIResponse:
        """テクニカル分析"""
        prompt = f"""
        銘柄コード: {symbol}
        現在価格: {market_data.get('current_price', 'N/A')}
        前日比: {market_data.get('change_percent', 'N/A')}%
        
        テクニカル指標:
        RSI: {market_data.get('rsi', 'N/A')}
        MACD: {market_data.get('macd', 'N/A')}
        ボリンジャーバンド: {market_data.get('bb_position', 'N/A')}
        移動平均: {market_data.get('sma_position', 'N/A')}
        
        上記データに基づいてテクニカル分析を実行してください。
        """
        
        request = AIRequest(
            analysis_type=AIAnalysisType.TECHNICAL,
            symbol=symbol,
            prompt=prompt
        )
        
        return await self.ai_service.analyze_with_fallback(request)

    async def _sentiment_analysis(self, symbol: str, market_data: Dict) -> AIResponse:
        """センチメント分析"""
        prompt = f"""
        銘柄コード: {symbol}
        
        最近の材料・ニュース:
        {market_data.get('recent_news', '情報なし')}
        
        市場環境:
        全体トレンド: {market_data.get('market_trend', 'N/A')}
        セクタートレンド: {market_data.get('sector_trend', 'N/A')}
        
        上記情報に基づいてセンチメント分析を実行してください。
        """
        
        request = AIRequest(
            analysis_type=AIAnalysisType.SENTIMENT,
            symbol=symbol,
            prompt=prompt
        )
        
        return await self.ai_service.analyze_with_fallback(request)

    async def _risk_analysis(self, symbol: str, market_data: Dict) -> AIResponse:
        """リスク分析"""
        prompt = f"""
        銘柄コード: {symbol}
        
        リスク情報:
        ボラティリティ: {market_data.get('volatility', 'N/A')}%
        ベータ値: {market_data.get('beta', 'N/A')}
        最大ドローダウン: {market_data.get('max_drawdown', 'N/A')}%
        
        市場リスク要因:
        {market_data.get('risk_factors', '通常レベル')}
        
        上記情報に基づいてリスク評価を実行してください。
        """
        
        request = AIRequest(
            analysis_type=AIAnalysisType.RISK,
            symbol=symbol,
            prompt=prompt
        )
        
        return await self.ai_service.analyze_with_fallback(request)

    async def _form_consensus(
        self, 
        results: List[AIResponse], 
        strategy: ConsensusStrategy
    ) -> Dict[str, Any]:
        """合意形成アルゴリズム"""
        
        decisions = [r.decision for r in results]
        confidences = [r.confidence for r in results]
        
        # 決定分布
        decision_counts = {"buy": 0, "sell": 0, "hold": 0}
        for decision in decisions:
            decision_counts[decision] += 1
        
        # 信頼度分布
        confidence_by_decision = {"buy": [], "sell": [], "hold": []}
        for result in results:
            confidence_by_decision[result.decision].append(result.confidence)
        
        # 戦略別合意形成
        if strategy == ConsensusStrategy.MAJORITY:
            consensus = self._majority_consensus(decision_counts, confidences)
        elif strategy == ConsensusStrategy.WEIGHTED_AVERAGE:
            consensus = self._weighted_consensus(results)
        elif strategy == ConsensusStrategy.CONSERVATIVE:
            consensus = self._conservative_consensus(results)
        elif strategy == ConsensusStrategy.AGGRESSIVE:
            consensus = self._aggressive_consensus(results)
        else:
            consensus = self._weighted_consensus(results)  # デフォルト
        
        # 合意度計算
        total_results = len(results)
        max_agreement = max(decision_counts.values())
        agreement_level = max_agreement / total_results if total_results > 0 else 0.0
        
        return {
            "decision": consensus["decision"],
            "confidence": consensus["confidence"],
            "reasoning": consensus["reasoning"],
            "agreement": agreement_level,
            "confidence_dist": {k: statistics.mean(v) if v else 0.0 for k, v in confidence_by_decision.items()},
            "decision_breakdown": decision_counts
        }

    def _majority_consensus(self, decision_counts: Dict, confidences: List[float]) -> Dict:
        """過半数決による合意"""
        majority_decision = max(decision_counts, key=decision_counts.get)
        avg_confidence = statistics.mean(confidences) if confidences else 0.5
        
        return {
            "decision": majority_decision,
            "confidence": avg_confidence,
            "reasoning": f"過半数決による判断: {majority_decision.upper()} (合意度: {max(decision_counts.values())}/{sum(decision_counts.values())})"
        }

    def _weighted_consensus(self, results: List[AIResponse]) -> Dict:
        """信頼度重み付き合意"""
        weighted_scores = {"buy": 0.0, "sell": 0.0, "hold": 0.0}
        total_weight = 0.0
        
        for result in results:
            weight = result.confidence
            weighted_scores[result.decision] += weight
            total_weight += weight
        
        # 正規化
        if total_weight > 0:
            for decision in weighted_scores:
                weighted_scores[decision] /= total_weight
        
        final_decision = max(weighted_scores, key=weighted_scores.get)
        final_confidence = weighted_scores[final_decision]
        
        reasoning_parts = [f"{r.decision.upper()}(信頼度{r.confidence:.2f})" for r in results]
        
        return {
            "decision": final_decision,
            "confidence": final_confidence,
            "reasoning": f"重み付き合意: {', '.join(reasoning_parts)} → {final_decision.upper()}"
        }

    def _conservative_consensus(self, results: List[AIResponse]) -> Dict:
        """保守的合意（リスク重視）"""
        # SELLまたはHOLDを優先
        decisions = [r.decision for r in results]
        
        if "sell" in decisions:
            sell_results = [r for r in results if r.decision == "sell"]
            avg_confidence = statistics.mean([r.confidence for r in sell_results])
            return {
                "decision": "sell",
                "confidence": avg_confidence,
                "reasoning": "保守的判断: リスク回避のため売却推奨"
            }
        elif "hold" in decisions:
            return {
                "decision": "hold",
                "confidence": 0.7,
                "reasoning": "保守的判断: 不確実性を考慮して保有継続"
            }
        else:
            return {
                "decision": "hold",
                "confidence": 0.5,
                "reasoning": "保守的判断: 全て買い推奨だが慎重に保有"
            }

    def _aggressive_consensus(self, results: List[AIResponse]) -> Dict:
        """積極的合意（収益重視）"""
        decisions = [r.decision for r in results]
        
        if "buy" in decisions:
            buy_results = [r for r in results if r.decision == "buy"]
            avg_confidence = statistics.mean([r.confidence for r in buy_results])
            return {
                "decision": "buy",
                "confidence": min(avg_confidence * 1.1, 1.0),  # 積極性ボーナス
                "reasoning": "積極的判断: 収益機会を重視して購入推奨"
            }
        else:
            return self._majority_consensus(
                {"buy": decisions.count("buy"), "sell": decisions.count("sell"), "hold": decisions.count("hold")},
                [r.confidence for r in results]
            )

    async def _broadcast_consensus_result(self, symbol: str, result: ConsensusResult):
        """WebSocketでリアルタイム配信"""
        try:
            await redis_client.publish(
                f"ai_consensus:{symbol}",
                json.dumps({
                    "symbol": symbol,
                    "decision": result.final_decision,
                    "confidence": result.consensus_confidence,
                    "agreement_level": result.agreement_level,
                    "processing_time": result.processing_time,
                    "total_cost": result.total_cost,
                    "timestamp": result.timestamp.isoformat()
                })
            )
        except Exception as e:
            logger.error(f"Failed to broadcast consensus result: {e}")

    async def get_model_performance_stats(self, days: int = 30) -> Dict[str, Any]:
        """モデル別パフォーマンス統計"""
        # Redis からパフォーマンスデータ取得
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # 実際の実装では Redis からデータ取得
        # ここでは概要のみ記載
        return {
            "period": f"{start_date.date()} to {end_date.date()}",
            "total_analyses": 0,
            "model_accuracy": {
                "gpt-4": {"accuracy": 0.75, "avg_confidence": 0.82},
                "claude-3": {"accuracy": 0.72, "avg_confidence": 0.78},
                "gemini-pro": {"accuracy": 0.68, "avg_confidence": 0.85}
            },
            "consensus_accuracy": 0.84,
            "cost_efficiency": {
                "total_cost": 0.0,
                "cost_per_analysis": 0.0,
                "roi_estimate": 0.0
            }
        }

# モデル最適化・自動調整機能
class ModelOptimizer:
    """AI モデル重み自動最適化"""
    
    def __init__(self):
        self.performance_history = []
    
    async def optimize_weights(self, historical_data: List[Dict]) -> ModelWeight:
        """過去のパフォーマンスに基づく重み最適化"""
        # 実装: 機械学習によるパラメータ最適化
        # 簡単な例として固定値を返す
        return ModelWeight(
            technical_weight=1.2,
            sentiment_weight=0.9,
            risk_weight=1.1,
            general_weight=0.5
        )
    
    def evaluate_prediction_accuracy(
        self, 
        predictions: List[ConsensusResult], 
        actual_outcomes: List[Dict]
    ) -> Dict[str, float]:
        """予測精度評価"""
        if not predictions or not actual_outcomes:
            return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0}
        
        correct_predictions = 0
        for pred, actual in zip(predictions, actual_outcomes):
            if pred.final_decision == actual.get("actual_direction"):
                correct_predictions += 1
        
        accuracy = correct_predictions / len(predictions)
        
        return {
            "accuracy": accuracy,
            "precision": accuracy,  # 簡易実装
            "recall": accuracy,     # 簡易実装
            "total_predictions": len(predictions)
        }

# 使用例
async def example_advanced_analysis():
    """高度AI分析の使用例"""
    try:
        async with AdvancedAIService() as ai_service:
            # サンプル市場データ
            market_data = {
                "current_price": 2650,
                "change_percent": 2.1,
                "rsi": 65.2,
                "macd": 0.15,
                "volatility": 18.5,
                "beta": 1.15,
                "recent_news": "新型車発表により株価上昇",
                "market_trend": "上昇トレンド"
            }
            
            # マルチモデル合意分析実行
            result = await ai_service.multi_model_consensus_analysis(
                symbol="7203",
                market_data=market_data,
                strategy=ConsensusStrategy.WEIGHTED_AVERAGE
            )
            
            print(f"合意判断: {result.final_decision}")
            print(f"合意信頼度: {result.consensus_confidence:.2f}")
            print(f"合意度: {result.agreement_level:.2f}")
            print(f"理由: {result.reasoning}")
            print(f"処理時間: {result.processing_time:.2f}秒")
            print(f"総コスト: ${result.total_cost:.4f}")
            
    except Exception as e:
        logger.error(f"Advanced analysis failed: {e}")

if __name__ == "__main__":
    asyncio.run(example_advanced_analysis())