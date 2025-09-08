import json
import uuid
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis
from app.config.settings import settings

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    WebSocket接続管理クラス - CloudRun対応のスケーラブル実装
    Redis Pub/Subを使用してインスタンス間でメッセージを配信
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # topic -> connection_ids
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        
    async def startup(self):
        """起動時の初期化処理"""
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL)
            await self.redis_client.ping()
            
            # Redis Pub/Sub リスナーを開始
            self.pubsub_task = asyncio.create_task(self._redis_listener())
            
            # ヘルスチェックタスク開始
            self.heartbeat_task = asyncio.create_task(self._heartbeat_checker())
            
            logger.info("WebSocket Manager initialized with Redis support")
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket Manager: {e}")
            # Redis無しでもローカル動作可能
            self.redis_client = None
    
    async def shutdown(self):
        """シャットダウン時のクリーンアップ"""
        if self.pubsub_task:
            self.pubsub_task.cancel()
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.redis_client:
            await self.redis_client.close()
        
        # 全接続を閉じる
        for connection_id in list(self.active_connections.keys()):
            await self.disconnect(connection_id)
    
    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None) -> str:
        """
        WebSocket接続を受け入れて管理
        
        Args:
            websocket: WebSocketインスタンス
            user_id: ユーザーID（認証済みの場合）
            
        Returns:
            str: 接続ID
        """
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow(),
            "client_info": websocket.headers
        }
        
        logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")
        
        # 接続成功メッセージを送信
        await self.send_to_connection(connection_id, {
            "type": "notification",
            "payload": {
                "message": "WebSocket接続が確立されました",
                "level": "success",
                "connection_id": connection_id
            }
        })
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """WebSocket接続を切断"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket {connection_id}: {e}")
            
            # メタデータとサブスクリプションをクリーンアップ
            del self.active_connections[connection_id]
            if connection_id in self.connection_metadata:
                del self.connection_metadata[connection_id]
            
            # サブスクリプションから削除
            for topic, connection_ids in self.subscriptions.items():
                connection_ids.discard(connection_id)
            
            logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """
        特定の接続にメッセージを送信
        フロントエンド互換のメッセージ形式
        """
        if connection_id not in self.active_connections:
            return False
            
        websocket = self.active_connections[connection_id]
        
        try:
            # フロントエンド期待形式にメッセージを正規化
            formatted_message = {
                "type": message.get("type", "notification"),
                "payload": message.get("payload", {}),
                "timestamp": message.get("timestamp", datetime.utcnow().isoformat()),
                "id": message.get("id", str(uuid.uuid4()))
            }
            
            await websocket.send_text(json.dumps(formatted_message))
            return True
            
        except WebSocketDisconnect:
            await self.disconnect(connection_id)
            return False
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
            await self.disconnect(connection_id)
            return False
    
    async def broadcast(self, message: Dict[str, Any], topic: Optional[str] = None):
        """
        メッセージをブロードキャスト
        
        Args:
            message: 送信するメッセージ
            topic: 特定のトピック購読者のみに送信（Noneの場合は全体）
        """
        # Redis経由でクラスター全体に配信
        if self.redis_client:
            redis_message = {
                "message": message,
                "topic": topic,
                "sender_instance": id(self)
            }
            
            channel = f"kaboom:websocket:{topic or 'broadcast'}"
            await self.redis_client.publish(channel, json.dumps(redis_message))
        
        # ローカルインスタンスの接続にも送信
        await self._send_to_local_connections(message, topic)
    
    async def _send_to_local_connections(self, message: Dict[str, Any], topic: Optional[str] = None):
        """ローカルインスタンスの接続にメッセージを送信"""
        if topic:
            # トピック購読者のみに送信
            connection_ids = self.subscriptions.get(topic, set())
        else:
            # 全接続に送信
            connection_ids = set(self.active_connections.keys())
        
        # 並行してメッセージ送信
        tasks = [
            self.send_to_connection(connection_id, message)
            for connection_id in connection_ids
        ]
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def subscribe_connection(self, connection_id: str, topic: str):
        """接続を特定のトピックに購読"""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        
        self.subscriptions[topic].add(connection_id)
        logger.debug(f"Connection {connection_id} subscribed to {topic}")
    
    async def unsubscribe_connection(self, connection_id: str, topic: str):
        """接続の特定のトピック購読を解除"""
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(connection_id)
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]
        
        logger.debug(f"Connection {connection_id} unsubscribed from {topic}")
    
    async def handle_message(self, connection_id: str, message: str):
        """クライアントからのメッセージを処理"""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            
            if message_type == "ping":
                # ハートビート応答
                await self.send_to_connection(connection_id, {
                    "type": "pong",
                    "payload": {"timestamp": datetime.utcnow().isoformat()}
                })
                
                # 最終ping時刻を更新
                if connection_id in self.connection_metadata:
                    self.connection_metadata[connection_id]["last_ping"] = datetime.utcnow()
            
            elif message_type == "subscribe":
                # トピック購読
                topic = data.get("payload", {}).get("topic")
                if topic:
                    await self.subscribe_connection(connection_id, topic)
                    await self.send_to_connection(connection_id, {
                        "type": "notification",
                        "payload": {
                            "message": f"トピック '{topic}' を購読しました",
                            "level": "info"
                        }
                    })
            
            elif message_type == "unsubscribe":
                # トピック購読解除
                topic = data.get("payload", {}).get("topic")
                if topic:
                    await self.unsubscribe_connection(connection_id, topic)
                    await self.send_to_connection(connection_id, {
                        "type": "notification",
                        "payload": {
                            "message": f"トピック '{topic}' の購読を解除しました",
                            "level": "info"
                        }
                    })
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from connection {connection_id}: {message}")
        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")
    
    async def _redis_listener(self):
        """Redis Pub/Sub リスナー"""
        if not self.redis_client:
            return
            
        pubsub = self.redis_client.pubsub()
        
        try:
            # 全てのWebSocketチャンネルを購読
            await pubsub.psubscribe("kaboom:websocket:*")
            
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        data = json.loads(message["data"])
                        
                        # 自分のインスタンスからの送信は無視
                        if data.get("sender_instance") == id(self):
                            continue
                        
                        # ローカル接続に転送
                        await self._send_to_local_connections(
                            data["message"],
                            data.get("topic")
                        )
                        
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
                        
        except asyncio.CancelledError:
            logger.info("Redis listener cancelled")
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
        finally:
            await pubsub.unsubscribe()
    
    async def _heartbeat_checker(self):
        """定期的にヘルスチェックを実行"""
        while True:
            try:
                await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                
                current_time = datetime.utcnow()
                stale_connections = []
                
                for connection_id, metadata in self.connection_metadata.items():
                    last_ping = metadata.get("last_ping", metadata["connected_at"])
                    if (current_time - last_ping).total_seconds() > settings.WS_HEARTBEAT_INTERVAL * 3:
                        stale_connections.append(connection_id)
                
                # 古い接続を切断
                for connection_id in stale_connections:
                    logger.info(f"Disconnecting stale connection: {connection_id}")
                    await self.disconnect(connection_id)
                
                logger.debug(f"Heartbeat check completed. Active connections: {len(self.active_connections)}")
                
            except asyncio.CancelledError:
                logger.info("Heartbeat checker cancelled")
                break
            except Exception as e:
                logger.error(f"Heartbeat checker error: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """接続統計情報を取得"""
        return {
            "active_connections": len(self.active_connections),
            "subscriptions": {topic: len(connections) for topic, connections in self.subscriptions.items()},
            "redis_connected": self.redis_client is not None,
            "uptime": "N/A"  # TODO: 起動時刻から計算
        }

# グローバルWebSocketマネージャーインスタンス
websocket_manager = WebSocketManager()