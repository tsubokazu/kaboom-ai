# app/services/tachibana_client.py

import asyncio
import aiohttp
import logging
import hmac
import hashlib
import base64
import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import uuid

from app.config.settings import settings
from app.services.redis_client import redis_client

logger = logging.getLogger(__name__)

class TachibanaOrderType(str, Enum):
    MARKET = "market"      # 成行
    LIMIT = "limit"        # 指値
    STOP = "stop"          # 逆指値
    STOP_LIMIT = "stop_limit"  # 逆指値付通常

class TachibanaOrderSide(str, Enum):
    BUY = "buy"           # 買い
    SELL = "sell"         # 売り

class TachibanaTimeInForce(str, Enum):
    DAY = "day"           # 当日中
    GTC = "gtc"           # 期限指定なし
    IOC = "ioc"           # Fill or Kill
    FOK = "fok"           # All or Nothing

@dataclass
class TachibanaOrder:
    """立花証券注文データ"""
    symbol: str
    side: TachibanaOrderSide
    order_type: TachibanaOrderType
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TachibanaTimeInForce = TachibanaTimeInForce.DAY
    client_order_id: Optional[str] = None

@dataclass
class TachibanaOrderStatus:
    """立花証券注文ステータス"""
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: int
    filled_quantity: int
    remaining_quantity: int
    price: Optional[float]
    average_price: Optional[float]
    status: str  # new, partially_filled, filled, cancelled, rejected
    commission: float
    timestamp: datetime
    error_message: Optional[str] = None

@dataclass
class TachibanaPosition:
    """立花証券ポジション情報"""
    symbol: str
    quantity: int
    average_cost: float
    current_price: float
    unrealized_pnl: float
    market_value: float
    last_updated: datetime

@dataclass
class TachibanaBalance:
    """立花証券残高情報"""
    cash_balance: float
    buying_power: float
    total_equity: float
    margin_used: float
    margin_available: float
    positions: List[TachibanaPosition]
    last_updated: datetime

class TachibanaError(Exception):
    """立花証券APIエラー"""
    pass

class TachibanaAuthError(TachibanaError):
    """立花証券認証エラー"""
    pass

class TachibanaRateLimitError(TachibanaError):
    """立花証券レート制限エラー"""
    pass

class TachibanaClient:
    """立花証券APIクライアント"""
    
    def __init__(self):
        self.api_key = settings.TACHIBANA_API_KEY
        self.api_secret = settings.TACHIBANA_API_SECRET
        self.base_url = "https://api.tachibana-sec.co.jp/v1"  # 仮のURL
        self.session: Optional[aiohttp.ClientSession] = None
        
        if not self.api_key or not self.api_secret:
            logger.warning("Tachibana API credentials not configured - using mock mode")
            self.mock_mode = True
        else:
            self.mock_mode = False
    
    async def __aenter__(self):
        if not self.mock_mode:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _generate_signature(self, method: str, path: str, timestamp: str, body: str = "") -> str:
        """API署名生成"""
        if self.mock_mode:
            return "mock_signature"
        
        message = f"{method}{path}{timestamp}{body}"
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _get_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """APIリクエストヘッダー生成"""
        timestamp = str(int(time.time() * 1000))
        signature = self._generate_signature(method, path, timestamp, body)
        
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "X-Timestamp": timestamp,
            "X-Signature": signature
        }
    
    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """APIリクエスト実行"""
        if self.mock_mode:
            return await self._mock_request(method, endpoint, data)
        
        url = f"{self.base_url}{endpoint}"
        body = json.dumps(data) if data else ""
        headers = self._get_headers(method, endpoint, body)
        
        try:
            async with self.session.request(method, url, headers=headers, data=body) as response:
                if response.status == 401:
                    raise TachibanaAuthError("Authentication failed")
                elif response.status == 429:
                    raise TachibanaRateLimitError("Rate limit exceeded")
                elif response.status >= 400:
                    error_data = await response.json()
                    raise TachibanaError(f"API error {response.status}: {error_data}")
                
                return await response.json()
                
        except aiohttp.ClientError as e:
            raise TachibanaError(f"Connection error: {e}")
    
    async def _mock_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """モックAPIレスポンス"""
        await asyncio.sleep(0.1)  # API応答時間をシミュレート
        
        if endpoint == "/orders" and method == "POST":
            return {
                "order_id": f"tachibana_order_{uuid.uuid4().hex[:12]}",
                "client_order_id": data.get("client_order_id", ""),
                "status": "new",
                "symbol": data.get("symbol"),
                "side": data.get("side"),
                "order_type": data.get("order_type"),
                "quantity": data.get("quantity"),
                "price": data.get("price"),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif endpoint.startswith("/orders/") and method == "GET":
            order_id = endpoint.split("/")[-1]
            return {
                "order_id": order_id,
                "status": "filled",
                "symbol": "7203",
                "side": "buy",
                "quantity": 100,
                "filled_quantity": 100,
                "average_price": 2650.0,
                "commission": 275.0,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif endpoint == "/account/balance" and method == "GET":
            return {
                "cash_balance": 1000000.0,
                "buying_power": 800000.0,
                "total_equity": 1200000.0,
                "margin_used": 200000.0,
                "margin_available": 600000.0,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif endpoint == "/account/positions" and method == "GET":
            return {
                "positions": [
                    {
                        "symbol": "7203",
                        "quantity": 100,
                        "average_cost": 2600.0,
                        "current_price": 2650.0,
                        "unrealized_pnl": 5000.0,
                        "market_value": 265000.0
                    },
                    {
                        "symbol": "6758", 
                        "quantity": 50,
                        "average_cost": 8500.0,
                        "current_price": 8200.0,
                        "unrealized_pnl": -15000.0,
                        "market_value": 410000.0
                    }
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif endpoint == "/market/quotes" and method == "GET":
            symbol = data.get("symbol", "7203") if data else "7203"
            return {
                "symbol": symbol,
                "bid": 2645.0,
                "ask": 2650.0,
                "last": 2648.0,
                "volume": 1250000,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        else:
            return {"status": "ok", "message": f"Mock response for {method} {endpoint}"}
    
    async def place_order(self, order: TachibanaOrder) -> TachibanaOrderStatus:
        """注文送信"""
        try:
            # クライアント注文IDがない場合は生成
            if not order.client_order_id:
                order.client_order_id = f"kb_{uuid.uuid4().hex[:12]}"
            
            # 注文データ構築
            order_data = {
                "symbol": order.symbol,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "quantity": order.quantity,
                "time_in_force": order.time_in_force.value,
                "client_order_id": order.client_order_id
            }
            
            if order.price:
                order_data["price"] = order.price
            if order.stop_price:
                order_data["stop_price"] = order.stop_price
            
            # API呼び出し
            response = await self._request("POST", "/orders", order_data)
            
            # レスポンスをTachibanaOrderStatusに変換
            return TachibanaOrderStatus(
                order_id=response["order_id"],
                client_order_id=response["client_order_id"],
                symbol=response["symbol"],
                side=response["side"],
                order_type=response["order_type"],
                quantity=response["quantity"],
                filled_quantity=0,
                remaining_quantity=response["quantity"],
                price=response.get("price"),
                average_price=None,
                status=response["status"],
                commission=0.0,
                timestamp=datetime.fromisoformat(response["timestamp"].replace("Z", "+00:00"))
            )
            
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            raise TachibanaError(f"注文送信エラー: {e}")
    
    async def get_order_status(self, order_id: str) -> TachibanaOrderStatus:
        """注文ステータス取得"""
        try:
            response = await self._request("GET", f"/orders/{order_id}")
            
            return TachibanaOrderStatus(
                order_id=response["order_id"],
                client_order_id=response.get("client_order_id", ""),
                symbol=response["symbol"],
                side=response["side"],
                order_type=response.get("order_type", ""),
                quantity=response["quantity"],
                filled_quantity=response.get("filled_quantity", 0),
                remaining_quantity=response.get("quantity", 0) - response.get("filled_quantity", 0),
                price=response.get("price"),
                average_price=response.get("average_price"),
                status=response["status"],
                commission=response.get("commission", 0.0),
                timestamp=datetime.fromisoformat(response["timestamp"].replace("Z", "+00:00")),
                error_message=response.get("error_message")
            )
            
        except Exception as e:
            logger.error(f"Order status retrieval failed: {e}")
            raise TachibanaError(f"注文ステータス取得エラー: {e}")
    
    async def cancel_order(self, order_id: str) -> bool:
        """注文キャンセル"""
        try:
            response = await self._request("DELETE", f"/orders/{order_id}")
            return response.get("status") == "cancelled"
        except Exception as e:
            logger.error(f"Order cancellation failed: {e}")
            return False
    
    async def get_balance(self) -> TachibanaBalance:
        """残高情報取得"""
        try:
            # 残高取得
            balance_response = await self._request("GET", "/account/balance")
            
            # ポジション取得
            positions_response = await self._request("GET", "/account/positions")
            
            positions = []
            for pos_data in positions_response.get("positions", []):
                positions.append(TachibanaPosition(
                    symbol=pos_data["symbol"],
                    quantity=pos_data["quantity"],
                    average_cost=pos_data["average_cost"],
                    current_price=pos_data["current_price"],
                    unrealized_pnl=pos_data["unrealized_pnl"],
                    market_value=pos_data["market_value"],
                    last_updated=datetime.utcnow()
                ))
            
            return TachibanaBalance(
                cash_balance=balance_response["cash_balance"],
                buying_power=balance_response["buying_power"],
                total_equity=balance_response["total_equity"],
                margin_used=balance_response["margin_used"],
                margin_available=balance_response["margin_available"],
                positions=positions,
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Balance retrieval failed: {e}")
            raise TachibanaError(f"残高取得エラー: {e}")
    
    async def get_market_quote(self, symbol: str) -> Dict[str, Any]:
        """市場価格取得"""
        try:
            response = await self._request("GET", "/market/quotes", {"symbol": symbol})
            return response
        except Exception as e:
            logger.error(f"Market quote retrieval failed: {e}")
            raise TachibanaError(f"市場価格取得エラー: {e}")
    
    async def get_order_history(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[TachibanaOrderStatus]:
        """注文履歴取得"""
        try:
            params = {"limit": limit}
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()
            
            response = await self._request("GET", "/orders/history", params)
            
            orders = []
            for order_data in response.get("orders", []):
                orders.append(TachibanaOrderStatus(
                    order_id=order_data["order_id"],
                    client_order_id=order_data.get("client_order_id", ""),
                    symbol=order_data["symbol"],
                    side=order_data["side"],
                    order_type=order_data.get("order_type", ""),
                    quantity=order_data["quantity"],
                    filled_quantity=order_data.get("filled_quantity", 0),
                    remaining_quantity=order_data.get("remaining_quantity", 0),
                    price=order_data.get("price"),
                    average_price=order_data.get("average_price"),
                    status=order_data["status"],
                    commission=order_data.get("commission", 0.0),
                    timestamp=datetime.fromisoformat(order_data["timestamp"].replace("Z", "+00:00"))
                ))
            
            return orders
            
        except Exception as e:
            logger.error(f"Order history retrieval failed: {e}")
            raise TachibanaError(f"注文履歴取得エラー: {e}")

class OrderExecutionService:
    """注文執行管理サービス"""
    
    def __init__(self):
        self.tachibana_client = None
        self.active_orders: Dict[str, TachibanaOrderStatus] = {}
        self.order_monitoring_task = None
    
    async def __aenter__(self):
        self.tachibana_client = await TachibanaClient().__aenter__()
        
        # 注文監視タスク開始
        self.order_monitoring_task = asyncio.create_task(self._monitor_orders())
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 注文監視タスク停止
        if self.order_monitoring_task:
            self.order_monitoring_task.cancel()
            try:
                await self.order_monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self.tachibana_client:
            await self.tachibana_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def execute_order(
        self,
        user_id: str,
        portfolio_id: str,
        symbol: str,
        side: str,
        order_type: str,
        quantity: int,
        price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """注文実行"""
        try:
            # 注文データ変換
            tachibana_order = TachibanaOrder(
                symbol=symbol,
                side=TachibanaOrderSide(side.lower()),
                order_type=TachibanaOrderType(order_type.lower()),
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                client_order_id=f"kb_{user_id[:8]}_{uuid.uuid4().hex[:8]}"
            )
            
            # 立花証券に注文送信
            order_status = await self.tachibana_client.place_order(tachibana_order)
            
            # アクティブ注文リストに追加
            self.active_orders[order_status.order_id] = order_status
            
            # Redis にキャッシュ
            await self._cache_order_status(order_status)
            
            # WebSocket で通知
            await self._notify_order_update(user_id, order_status, "order_placed")
            
            return {
                "external_order_id": order_status.order_id,
                "client_order_id": order_status.client_order_id,
                "status": order_status.status,
                "symbol": order_status.symbol,
                "side": order_status.side,
                "quantity": order_status.quantity,
                "price": order_status.price,
                "timestamp": order_status.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            raise TachibanaError(f"注文実行エラー: {e}")
    
    async def _monitor_orders(self):
        """注文監視ループ"""
        while True:
            try:
                # アクティブ注文の状態チェック
                for order_id in list(self.active_orders.keys()):
                    try:
                        updated_status = await self.tachibana_client.get_order_status(order_id)
                        old_status = self.active_orders[order_id]
                        
                        # ステータス変更があった場合
                        if updated_status.status != old_status.status or \
                           updated_status.filled_quantity != old_status.filled_quantity:
                            
                            self.active_orders[order_id] = updated_status
                            await self._cache_order_status(updated_status)
                            
                            # WebSocket通知
                            await self._notify_order_update(
                                "user_from_order",  # 実際の実装では注文からユーザーIDを取得
                                updated_status,
                                "order_updated"
                            )
                            
                            # 完了した注文はアクティブリストから削除
                            if updated_status.status in ["filled", "cancelled", "rejected"]:
                                del self.active_orders[order_id]
                                
                    except Exception as e:
                        logger.error(f"Order monitoring failed for {order_id}: {e}")
                
                await asyncio.sleep(5)  # 5秒間隔でチェック
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Order monitoring loop error: {e}")
                await asyncio.sleep(10)
    
    async def _cache_order_status(self, order_status: TachibanaOrderStatus):
        """注文ステータスキャッシュ"""
        try:
            cache_data = {
                "order_id": order_status.order_id,
                "status": order_status.status,
                "symbol": order_status.symbol,
                "filled_quantity": order_status.filled_quantity,
                "average_price": order_status.average_price,
                "commission": order_status.commission,
                "timestamp": order_status.timestamp.isoformat()
            }
            
            await redis_client.set(
                f"tachibana_order:{order_status.order_id}",
                json.dumps(cache_data),
                expire=3600
            )
        except Exception as e:
            logger.error(f"Order caching failed: {e}")
    
    async def _notify_order_update(self, user_id: str, order_status: TachibanaOrderStatus, event_type: str):
        """注文更新通知"""
        try:
            notification_data = {
                "type": event_type,
                "order_id": order_status.order_id,
                "symbol": order_status.symbol,
                "status": order_status.status,
                "filled_quantity": order_status.filled_quantity,
                "timestamp": order_status.timestamp.isoformat()
            }
            
            # WebSocket経由でユーザーに通知
            await redis_client.publish(
                f"order_updates:{user_id}",
                json.dumps(notification_data)
            )
        except Exception as e:
            logger.error(f"Order notification failed: {e}")
    
    async def get_account_balance(self) -> TachibanaBalance:
        """口座残高取得"""
        return await self.tachibana_client.get_balance()
    
    async def sync_positions_with_portfolio(self, user_id: str, portfolio_id: str):
        """ポートフォリオとの同期"""
        try:
            # 立花証券からポジション取得
            balance = await self.tachibana_client.get_balance()
            
            # データベースのポートフォリオと同期
            # 実際の実装では portfolio_service を使用
            logger.info(f"Syncing {len(balance.positions)} positions for user {user_id}")
            
        except Exception as e:
            logger.error(f"Position sync failed: {e}")

# グローバルインスタンス
order_execution_service = OrderExecutionService()