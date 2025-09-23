"""
Redis統合クライアント - セッション管理・キャッシング・Pub/Sub基盤

Phase 2A: Redis統合基盤
- セッション管理（JWT token + user data）
- データキャッシング（価格情報・分析結果）
- Pub/Sub配信（WebSocket real-time updates）
- Celeryジョブキュー管理
"""
import json
import logging
import os
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta

import redis.asyncio as redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis統合クライアント - 全てのRedis操作を統一管理"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.pool = None
        self.client = None
        
    async def connect(self):
        """Redis接続初期化"""
        try:
            self.pool = redis.ConnectionPool.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True
            )
            self.client = redis.Redis(connection_pool=self.pool)
            
            # 接続テスト
            await self.client.ping()
            logger.info(f"Redis connected successfully: {self.redis_url}")
            
        except RedisConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Redis initialization error: {e}")
            raise
    
    async def disconnect(self):
        """Redis接続クローズ"""
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()
    
    async def health_check(self) -> Dict[str, Any]:
        """Redis接続状態確認"""
        try:
            if not self.client:
                return {"status": "disconnected", "error": "Client not initialized"}
            
            # 基本接続テスト
            ping_result = await self.client.ping()
            
            # メモリ使用量確認
            info = await self.client.info("memory")
            
            return {
                "status": "connected",
                "ping": ping_result,
                "memory_usage": info.get("used_memory_human", "unknown"),
                "max_memory": info.get("maxmemory_human", "unlimited")
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {"status": "error", "error": str(e)}

    # ================================
    # セッション管理機能
    # ================================
    
    async def set_session(self, session_id: str, user_data: Dict, expire_seconds: int = 1800):
        """ユーザーセッション保存（JWT + user info）"""
        try:
            session_key = f"session:{session_id}"
            session_data = {
                "user_id": user_data.get("user_id"),
                "email": user_data.get("email"),
                "role": user_data.get("role", "basic"),
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(seconds=expire_seconds)).isoformat()
            }
            
            await self.client.setex(
                session_key, 
                expire_seconds, 
                json.dumps(session_data)
            )
            
            logger.info(f"Session stored: {session_id} for user {user_data.get('user_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Session storage failed: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """セッション取得・検証"""
        try:
            session_key = f"session:{session_id}"
            session_data = await self.client.get(session_key)
            
            if not session_data:
                return None
            
            return json.loads(session_data)
            
        except Exception as e:
            logger.error(f"Session retrieval failed: {e}")
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """セッション削除（ログアウト）"""
        try:
            session_key = f"session:{session_id}"
            result = await self.client.delete(session_key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Session deletion failed: {e}")
            return False

    # ================================
    # データキャッシング機能
    # ================================
    
    async def set_cache(self, key: str, data: Any, expire_seconds: int = 300):
        """汎用データキャッシング"""
        try:
            cache_key = f"cache:{key}"
            serialized_data = json.dumps(data, default=str)

            await self.client.setex(cache_key, expire_seconds, serialized_data)
            return True

        except Exception as e:
            logger.error(f"Cache storage failed for {key}: {e}")
            return False
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """キャッシュデータ取得"""
        try:
            cache_key = f"cache:{key}"
            cached_data = await self.client.get(cache_key)
            
            if not cached_data:
                return None
            
            return json.loads(cached_data)
            
        except Exception as e:
            logger.error(f"Cache retrieval failed for {key}: {e}")
            return None
    
    async def delete_cache(self, key: str) -> bool:
        """キャッシュ削除"""
        try:
            cache_key = f"cache:{key}"
            result = await self.client.delete(cache_key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Cache deletion failed for {key}: {e}")
            return False
    
    # 価格情報専用キャッシング
    async def set_stock_price(self, symbol: str, price_data: Dict, expire_seconds: int = 60):
        """株価データキャッシング（高頻度更新）"""
        return await self.set_cache(f"stock_price:{symbol}", price_data, expire_seconds)
    
    async def get_stock_price(self, symbol: str) -> Optional[Dict]:
        """株価データ取得"""
        return await self.get_cache(f"stock_price:{symbol}")
    
    # AI分析結果キャッシング
    async def set_ai_analysis(self, request_id: str, analysis_result: Dict, expire_seconds: int = 3600):
        """AI分析結果キャッシング（長時間保持）"""
        return await self.set_cache(f"ai_analysis:{request_id}", analysis_result, expire_seconds)
    
    async def get_ai_analysis(self, request_id: str) -> Optional[Dict]:
        """AI分析結果取得"""
        return await self.get_cache(f"ai_analysis:{request_id}")

    # ================================
    # Pub/Sub配信機能（WebSocket用）
    # ================================
    
    async def publish_message(self, channel: str, message: Dict) -> bool:
        """メッセージ配信（WebSocket経由で全クライアントに送信）"""
        try:
            message_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "channel": channel,
                "data": message
            }
            
            result = await self.client.publish(
                channel, 
                json.dumps(message_data, default=str)
            )
            
            logger.info(f"Published to {channel}: {result} subscribers")
            return result > 0
            
        except Exception as e:
            logger.error(f"Message publishing failed for {channel}: {e}")
            return False

    # 後方互換のためのラッパーメソッド
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """setex を伴うシンプルな値保存（既存コード互換用）"""
        if not self.client:
            raise RuntimeError("Redis client is not connected")
        try:
            if expire is not None and expire > 0:
                await self.client.setex(key, expire, value)
            else:
                await self.client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis set failed for {key}: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """値を取得（既存コード互換用）"""
        if not self.client:
            raise RuntimeError("Redis client is not connected")
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Redis get failed for {key}: {e}")
            return None

    async def publish(self, channel: str, message: Any) -> bool:
        """publish_message のラッパー（既存コード互換用）"""
        payload = message
        if not isinstance(message, str):
            payload = json.dumps(message, default=str)
        try:
            result = await self.client.publish(channel, payload)
            return result > 0
        except Exception as e:
            logger.error(f"Redis publish failed for {channel}: {e}")
            return False
    
    async def subscribe_channel(self, channel: str, callback: Callable):
        """チャンネル購読（WebSocketサーバー側で使用）"""
        try:
            pubsub = self.client.pubsub()
            await pubsub.subscribe(channel)
            
            logger.info(f"Subscribed to channel: {channel}")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        await callback(data)
                    except Exception as e:
                        logger.error(f"Message callback error: {e}")
            
        except Exception as e:
            logger.error(f"Subscription error for {channel}: {e}")
    
    # 専用チャンネル配信
    async def publish_price_update(self, symbol: str, price_data: Dict) -> bool:
        """株価更新配信"""
        return await self.publish_message(f"price_update:{symbol}", price_data)
    
    async def publish_portfolio_update(self, user_id: str, portfolio_data: Dict) -> bool:
        """ポートフォリオ更新配信"""
        return await self.publish_message(f"portfolio_update:{user_id}", portfolio_data)
    
    async def publish_ai_analysis_complete(self, request_id: str, analysis_result: Dict) -> bool:
        """AI分析完了通知配信"""
        return await self.publish_message(f"ai_analysis_complete:{request_id}", analysis_result)

    # ================================
    # Celeryジョブ管理機能
    # ================================
    
    async def set_job_status(self, job_id: str, status: str, result: Optional[Dict] = None, expire_seconds: int = 3600):
        """ジョブ状態管理（Celery補完）"""
        try:
            job_key = f"job:{job_id}"
            job_data = {
                "status": status,  # pending, running, completed, failed
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "result": result
            }
            
            await self.client.setex(job_key, expire_seconds, json.dumps(job_data, default=str))
            
            # リアルタイム通知
            await self.publish_message(f"job_status:{job_id}", job_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Job status update failed for {job_id}: {e}")
            return False
    
    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """ジョブ状態取得"""
        try:
            job_key = f"job:{job_id}"
            job_data = await self.client.get(job_key)
            
            if not job_data:
                return None
            
            return json.loads(job_data)
            
        except Exception as e:
            logger.error(f"Job status retrieval failed for {job_id}: {e}")
            return None

    # ================================
    # メンテナンス機能
    # ================================
    
    async def clear_expired_cache(self) -> int:
        """期限切れキャッシュクリーンアップ"""
        try:
            # Redisが自動的にTTL管理しているため、手動クリーンアップは通常不要
            # ただし、特定パターンのキーを削除したい場合
            keys = await self.client.keys("cache:*")
            expired_count = 0
            
            for key in keys:
                ttl = await self.client.ttl(key)
                if ttl == -2:  # キーが存在しない
                    expired_count += 1
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            return 0


# グローバルRedisクライアントインスタンス
redis_client = RedisClient()


# FastAPI依存性注入用
async def get_redis_client() -> RedisClient:
    """Redis クライアント依存性注入"""
    if not redis_client.client:
        await redis_client.connect()
    return redis_client
