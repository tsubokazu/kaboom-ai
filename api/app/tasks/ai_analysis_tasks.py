"""
AI分析タスク - OpenRouter統合による非同期AI分析処理

機能:
- 複数AIモデルによる並列分析・合意形成
- 結果のRedis保存・WebSocket配信
- タスク進行状況リアルタイム通知
- エラーハンドリング・リトライ機能
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from celery import Task
from app.tasks.celery_app import celery_app
from app.services.openrouter_client import OpenRouterClient, AIRequest, AIAnalysisType
from app.services.redis_client import get_redis_client
from app.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """コールバック機能付きタスクベースクラス"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """タスク成功時のコールバック"""
        logger.info(f"Task {task_id} completed successfully")
        
    def on_failure(self, exc, task_id, args, kwargs, traceback):
        """タスク失敗時のコールバック"""
        logger.error(f"Task {task_id} failed: {exc}")


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="ai_analysis.stock_technical_analysis",
    queue="ai_analysis",
    soft_time_limit=180,
    time_limit=300,
    retry_kwargs={"max_retries": 2, "countdown": 60}
)
def stock_technical_analysis_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    株式テクニカル分析タスク
    
    Args:
        request_data: {
            "symbol": "7203",
            "user_id": "user123",
            "analysis_options": {...}
        }
    
    Returns:
        分析結果辞書
    """
    request_id = self.request.id
    symbol = request_data.get("symbol")
    user_id = request_data.get("user_id")
    
    try:
        # タスク開始通知
        asyncio.run(_update_task_status(
            request_id, "running", 
            {"message": f"テクニカル分析開始: {symbol}", "progress": 10}
        ))
        
        # AI分析実行（非同期処理をsyncラッパーで実行）
        analysis_result = asyncio.run(_perform_technical_analysis(symbol, request_data))
        
        # 結果をRedisに保存
        asyncio.run(_save_analysis_result(request_id, analysis_result))
        
        # WebSocket経由で結果通知
        if user_id:
            asyncio.run(_notify_analysis_complete(request_id, user_id, analysis_result))
        
        # タスク完了通知
        asyncio.run(_update_task_status(
            request_id, "completed", 
            {"message": "テクニカル分析完了", "progress": 100}
        ))
        
        return {
            "status": "success",
            "request_id": request_id,
            "symbol": symbol,
            "analysis": analysis_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Technical analysis task failed: {e}")
        
        # エラー状況をユーザーに通知
        asyncio.run(_update_task_status(
            request_id, "failed", 
            {"error": str(e), "message": "テクニカル分析に失敗しました"}
        ))
        
        # リトライまたは失敗
        if self.request.retries < self.retry_kwargs['max_retries']:
            raise self.retry(exc=e)
        
        raise


@celery_app.task(
    bind=True,
    base=CallbackTask, 
    name="ai_analysis.sentiment_analysis",
    queue="ai_analysis",
    soft_time_limit=120,
    time_limit=180
)
def sentiment_analysis_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """センチメント分析タスク"""
    request_id = self.request.id
    symbol = request_data.get("symbol")
    user_id = request_data.get("user_id")
    
    try:
        # 進行状況通知
        asyncio.run(_update_task_status(
            request_id, "running", 
            {"message": f"センチメント分析開始: {symbol}", "progress": 20}
        ))
        
        # AI分析実行
        analysis_result = asyncio.run(_perform_sentiment_analysis(symbol, request_data))
        
        # 結果保存・通知
        asyncio.run(_save_analysis_result(request_id, analysis_result))
        
        if user_id:
            asyncio.run(_notify_analysis_complete(request_id, user_id, analysis_result))
        
        return {
            "status": "success", 
            "request_id": request_id,
            "symbol": symbol,
            "analysis": analysis_result
        }
        
    except Exception as e:
        logger.error(f"Sentiment analysis task failed: {e}")
        raise


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="ai_analysis.multi_model_analysis", 
    queue="ai_analysis",
    soft_time_limit=300,
    time_limit=420
)
def multi_model_analysis_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    複数AIモデル並列分析・合意形成タスク
    GPT-4, Claude, Geminiによる分析結果を統合
    """
    request_id = self.request.id
    symbol = request_data.get("symbol")
    user_id = request_data.get("user_id")
    
    try:
        # 進行状況通知
        asyncio.run(_update_task_status(
            request_id, "running",
            {"message": f"マルチモデル分析開始: {symbol}", "progress": 5}
        ))
        
        # 並列AI分析実行
        analysis_results = asyncio.run(_perform_multi_model_analysis(symbol, request_data, request_id))
        
        # 合意形成処理
        asyncio.run(_update_task_status(
            request_id, "running",
            {"message": "分析結果の合意形成処理中...", "progress": 80}
        ))
        
        consensus_result = asyncio.run(_generate_consensus_analysis(analysis_results))
        
        # 最終結果保存・通知
        final_result = {
            "consensus": consensus_result,
            "individual_analyses": analysis_results,
            "model_agreement_score": _calculate_agreement_score(analysis_results)
        }
        
        asyncio.run(_save_analysis_result(request_id, final_result))
        
        if user_id:
            asyncio.run(_notify_analysis_complete(request_id, user_id, final_result))
        
        asyncio.run(_update_task_status(
            request_id, "completed",
            {"message": "マルチモデル分析完了", "progress": 100}
        ))
        
        return {
            "status": "success",
            "request_id": request_id, 
            "symbol": symbol,
            "analysis": final_result,
            "models_used": len(analysis_results)
        }
        
    except Exception as e:
        logger.error(f"Multi-model analysis task failed: {e}")
        raise


@celery_app.task(name="ai_analysis.cleanup_expired_analysis", queue="ai_analysis")
def cleanup_expired_analysis():
    """期限切れAI分析結果クリーンアップ"""
    try:
        cleanup_count = asyncio.run(_cleanup_expired_results())
        return {"cleaned_up": cleanup_count, "status": "success"}
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        return {"error": str(e), "status": "failed"}


# ===================================
# 内部ヘルパー関数（非同期処理）
# ===================================

async def _perform_technical_analysis(symbol: str, request_data: Dict) -> Dict[str, Any]:
    """テクニカル分析実行"""
    async with OpenRouterClient() as client:
        ai_request = AIRequest(
            analysis_type=AIAnalysisType.TECHNICAL,
            symbol=symbol,
            prompt=f"{symbol}の株価テクニカル分析を実行してください。",
            model="openai/gpt-4-turbo-preview",
            max_tokens=1000
        )
        
        response = await client.analyze_stock(ai_request)
        
        return {
            "type": "technical_analysis",
            "symbol": symbol,
            "analysis": response.analysis,
            "model": response.model,
            "confidence": response.confidence,
            "cost_usd": response.cost_usd
        }


async def _perform_sentiment_analysis(symbol: str, request_data: Dict) -> Dict[str, Any]:
    """センチメント分析実行"""
    async with OpenRouterClient() as client:
        ai_request = AIRequest(
            analysis_type=AIAnalysisType.SENTIMENT,
            symbol=symbol,
            prompt=f"{symbol}の市場センチメント分析を実行してください。",
            model="anthropic/claude-3-sonnet",
            max_tokens=800
        )
        
        response = await client.analyze_stock(ai_request)
        
        return {
            "type": "sentiment_analysis",
            "symbol": symbol, 
            "analysis": response.analysis,
            "model": response.model,
            "sentiment_score": response.confidence,
            "cost_usd": response.cost_usd
        }


async def _perform_multi_model_analysis(symbol: str, request_data: Dict, request_id: str) -> List[Dict[str, Any]]:
    """複数モデル並列分析"""
    models = [
        ("openai/gpt-4-turbo-preview", AIAnalysisType.TECHNICAL),
        ("anthropic/claude-3-sonnet", AIAnalysisType.SENTIMENT),
        ("google/gemini-pro", AIAnalysisType.RISK)
    ]
    
    results = []
    
    async with OpenRouterClient() as client:
        tasks = []
        
        for i, (model, analysis_type) in enumerate(models):
            # 進行状況更新
            await _update_task_status(
                request_id, "running",
                {"message": f"{model}による分析実行中...", "progress": 20 + i * 20}
            )
            
            ai_request = AIRequest(
                analysis_type=analysis_type,
                symbol=symbol,
                prompt=f"{symbol}の{analysis_type.value}分析を実行してください。",
                model=model,
                max_tokens=1000
            )
            
            tasks.append(client.analyze_stock(ai_request))
        
        # 並列実行
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.warning(f"Model {models[i][0]} analysis failed: {response}")
                continue
                
            results.append({
                "model": response.model,
                "analysis_type": models[i][1].value,
                "analysis": response.analysis,
                "confidence": response.confidence,
                "cost_usd": response.cost_usd
            })
    
    return results


async def _generate_consensus_analysis(individual_analyses: List[Dict]) -> Dict[str, Any]:
    """個別分析結果から合意形成"""
    if not individual_analyses:
        return {"consensus": "分析結果なし", "confidence": 0}
    
    # 簡単な合意形成ロジック（実際はより複雑なアルゴリズムを使用）
    total_confidence = sum(analysis.get("confidence", 0) for analysis in individual_analyses)
    avg_confidence = total_confidence / len(individual_analyses)
    
    return {
        "consensus": "複数モデルによる総合分析結果",
        "confidence": avg_confidence,
        "models_count": len(individual_analyses),
        "summary": "テクニカル・センチメント・リスク分析の統合結果"
    }


def _calculate_agreement_score(analyses: List[Dict]) -> float:
    """モデル間の合意度計算"""
    if len(analyses) < 2:
        return 1.0
    
    # 信頼度の分散から合意度を計算
    confidences = [analysis.get("confidence", 0) for analysis in analyses]
    variance = sum((c - sum(confidences)/len(confidences))**2 for c in confidences) / len(confidences)
    
    # 分散が小さいほど合意度が高い（0-1のスケール）
    agreement_score = max(0, 1 - variance)
    
    return round(agreement_score, 3)


async def _update_task_status(task_id: str, status: str, details: Dict[str, Any]):
    """タスク状況をRedis/WebSocketに更新"""
    try:
        redis_client = await get_redis_client()
        
        # Redis状態更新
        await redis_client.set_job_status(task_id, status, details)
        
        # WebSocket通知（グローバル・リアルタイム通知）
        await websocket_manager.broadcast({
            "type": "task_progress",
            "payload": {
                "task_id": task_id,
                "status": status,
                "details": details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }, "task_updates")
        
    except Exception as e:
        logger.warning(f"Failed to update task status: {e}")


async def _save_analysis_result(request_id: str, result: Dict[str, Any]):
    """分析結果をRedisに保存"""
    try:
        redis_client = await get_redis_client()
        await redis_client.set_ai_analysis(request_id, result, expire_seconds=7200)  # 2時間保持
        
    except Exception as e:
        logger.error(f"Failed to save analysis result: {e}")


async def _notify_analysis_complete(request_id: str, user_id: str, result: Dict[str, Any]):
    """AI分析完了をユーザーにWebSocket通知"""
    try:
        await websocket_manager.send_ai_analysis_result(request_id, user_id, result)
        
    except Exception as e:
        logger.error(f"Failed to notify analysis completion: {e}")


async def _cleanup_expired_results() -> int:
    """期限切れ分析結果クリーンアップ"""
    try:
        redis_client = await get_redis_client()
        # Redis TTLによる自動削除を利用（手動クリーンアップは最小限）
        return await redis_client.clear_expired_cache()
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return 0