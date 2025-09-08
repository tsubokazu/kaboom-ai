import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import random

import yfinance as yf
import psutil
import pandas as pd
from app.websocket.manager import websocket_manager
from app.config.settings import settings

logger = logging.getLogger(__name__)

class RealtimeService:
    """リアルタイムデータ配信サービス"""
    
    def __init__(self):
        self.is_running = False
        self.tasks: List[asyncio.Task] = []
        
        # デフォルトの監視銘柄
        self.watched_symbols = [
            "7203.T",   # トヨタ
            "6758.T",   # ソニー
            "9984.T",   # ソフトバンク
            "8058.T",   # 三菱商事
            "6861.T",   # キーエンス
            "AAPL",     # Apple
            "GOOGL",    # Google
            "MSFT",     # Microsoft
            "TSLA",     # Tesla
            "NVDA"      # NVIDIA
        ]
        
        # 価格データキャッシュ
        self.price_cache: Dict[str, Dict] = {}
        
    async def start(self):
        """サービス開始"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("Starting RealtimeService")
        
        # 各データ配信タスクを開始
        self.tasks = [
            asyncio.create_task(self._price_data_loop()),
            asyncio.create_task(self._system_metrics_loop()),
            asyncio.create_task(self._market_status_loop()),
        ]
        
    async def stop(self):
        """サービス停止"""
        self.is_running = False
        
        # 全タスクをキャンセル
        for task in self.tasks:
            task.cancel()
        
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        
        logger.info("RealtimeService stopped")
    
    async def _price_data_loop(self):
        """価格データの定期更新と配信"""
        while self.is_running:
            try:
                await self._update_and_broadcast_prices()
                await asyncio.sleep(settings.MARKET_DATA_UPDATE_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("Price data loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in price data loop: {e}")
                await asyncio.sleep(10)  # エラー時は10秒待機
    
    async def _update_and_broadcast_prices(self):
        """価格データの更新と配信"""
        try:
            # 非同期で価格データ取得（実際の実装では外部APIを使用）
            for symbol in self.watched_symbols:
                # モック価格データ生成（yfinanceは重いので開発時はモックを使用）
                if settings.DEBUG:
                    price_data = await self._generate_mock_price_data(symbol)
                else:
                    price_data = await self._fetch_real_price_data(symbol)
                
                # キャッシュ更新
                self.price_cache[symbol] = price_data
                
                # WebSocket配信
                await websocket_manager.broadcast({
                    "type": "price_update",
                    "payload": {
                        "symbol": symbol,
                        "price": price_data["price"],
                        "change": price_data["change"],
                        "change_percent": price_data["change_percent"],
                        "volume": price_data["volume"],
                        "timestamp": price_data["timestamp"],
                        "market_status": price_data.get("market_status", "open")
                    }
                }, topic="price_update")
                
                # 少し間隔を空けて負荷分散
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error updating price data: {e}")
    
    async def _generate_mock_price_data(self, symbol: str) -> Dict:
        """モック価格データ生成"""
        # 前回価格を基準にランダム変動
        base_prices = {
            "7203.T": 2000, "6758.T": 10000, "9984.T": 1500, "8058.T": 3500, "6861.T": 45000,
            "AAPL": 175, "GOOGL": 2800, "MSFT": 350, "TSLA": 250, "NVDA": 900
        }
        
        base_price = base_prices.get(symbol, 100)
        
        # ランダム変動（-2% ~ +2%）
        change_percent = random.uniform(-2.0, 2.0)
        change = base_price * (change_percent / 100)
        current_price = base_price + change
        
        return {
            "symbol": symbol,
            "price": round(current_price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "volume": random.randint(100000, 10000000),
            "timestamp": datetime.utcnow().isoformat(),
            "market_status": "open" if 9 <= datetime.utcnow().hour < 15 else "closed"
        }
    
    async def _fetch_real_price_data(self, symbol: str) -> Dict:
        """実際の価格データ取得"""
        try:
            # yfinance は同期APIなので thread_pool で実行
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
            info = await loop.run_in_executor(None, lambda: ticker.info)
            
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            previous_close = info.get('previousClose', current_price)
            
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100 if previous_close > 0 else 0
            
            return {
                "symbol": symbol,
                "price": round(current_price, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "volume": info.get('volume', 0),
                "timestamp": datetime.utcnow().isoformat(),
                "market_status": info.get('marketState', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Error fetching real price data for {symbol}: {e}")
            # エラー時はモックデータで代替
            return await self._generate_mock_price_data(symbol)
    
    async def _system_metrics_loop(self):
        """システムメトリクスの定期配信"""
        while self.is_running:
            try:
                await self._broadcast_system_metrics()
                await asyncio.sleep(settings.SYSTEM_METRICS_UPDATE_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("System metrics loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in system metrics loop: {e}")
                await asyncio.sleep(10)
    
    async def _broadcast_system_metrics(self):
        """システムメトリクスの取得と配信"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            
            # WebSocket接続統計
            ws_stats = websocket_manager.get_connection_stats()
            
            metrics = {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "websocket": ws_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # WebSocket配信
            await websocket_manager.broadcast({
                "type": "system_metrics",
                "payload": metrics
            }, topic="system_metrics")
            
        except Exception as e:
            logger.error(f"Error broadcasting system metrics: {e}")
    
    async def _market_status_loop(self):
        """市場状況の定期配信"""
        while self.is_running:
            try:
                await self._broadcast_market_status()
                await asyncio.sleep(300)  # 5分間隔
                
            except asyncio.CancelledError:
                logger.info("Market status loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in market status loop: {e}")
                await asyncio.sleep(30)
    
    async def _broadcast_market_status(self):
        """市場状況の配信"""
        try:
            current_time = datetime.utcnow()
            
            # 簡単な市場状況判定
            is_market_hours = 9 <= current_time.hour < 15
            
            market_status = {
                "status": "open" if is_market_hours else "closed",
                "next_open": None,  # TODO: 実装
                "timezone": "JST",
                "indices": {
                    "nikkei225": random.randint(28000, 32000),  # モック
                    "topix": random.randint(1900, 2100),       # モック
                    "dow": random.randint(33000, 36000),       # モック
                    "nasdaq": random.randint(13000, 15000)     # モック
                },
                "timestamp": current_time.isoformat()
            }
            
            await websocket_manager.broadcast({
                "type": "market_status",
                "payload": market_status
            }, topic="market_status")
            
        except Exception as e:
            logger.error(f"Error broadcasting market status: {e}")
    
    async def trigger_ai_analysis(self, symbol: str, analysis_type: str = "technical") -> Dict:
        """AI分析をトリガーして結果を配信"""
        try:
            # AI分析処理中の通知
            await websocket_manager.broadcast({
                "type": "notification",
                "payload": {
                    "message": f"{symbol}の{analysis_type}分析を開始しています...",
                    "level": "info"
                }
            })
            
            # モックAI分析結果生成
            analysis_result = await self._generate_mock_ai_analysis(symbol, analysis_type)
            
            # 分析結果を配信
            await websocket_manager.broadcast({
                "type": "ai_analysis",
                "payload": analysis_result
            }, topic="ai_analysis")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in AI analysis for {symbol}: {e}")
            
            await websocket_manager.broadcast({
                "type": "notification",
                "payload": {
                    "message": f"{symbol}の分析でエラーが発生しました: {str(e)}",
                    "level": "error"
                }
            })
            
            raise
    
    async def _generate_mock_ai_analysis(self, symbol: str, analysis_type: str) -> Dict:
        """モックAI分析結果生成"""
        # 分析処理のシミュレーション
        await asyncio.sleep(2)
        
        recommendations = ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
        confidence_levels = ["HIGH", "MEDIUM", "LOW"]
        
        return {
            "symbol": symbol,
            "analysis_type": analysis_type,
            "recommendation": random.choice(recommendations),
            "confidence": random.choice(confidence_levels),
            "target_price": random.uniform(1000, 5000),
            "risk_level": random.choice(["LOW", "MEDIUM", "HIGH"]),
            "key_factors": [
                "技術指標が強気シグナルを示している",
                "市場センチメントが改善傾向",
                "業績予想の上方修正期待"
            ],
            "price_prediction": {
                "1week": random.uniform(-5, 5),
                "1month": random.uniform(-10, 10),
                "3month": random.uniform(-15, 15)
            },
            "generated_at": datetime.utcnow().isoformat(),
            "model_version": "kaboom-ai-v1.0"
        }
    
    def get_current_prices(self) -> Dict[str, Dict]:
        """現在の価格データを取得"""
        return self.price_cache.copy()
    
    def add_watched_symbol(self, symbol: str):
        """監視銘柄を追加"""
        if symbol not in self.watched_symbols:
            self.watched_symbols.append(symbol)
            logger.info(f"Added watched symbol: {symbol}")
    
    def remove_watched_symbol(self, symbol: str):
        """監視銘柄を削除"""
        if symbol in self.watched_symbols:
            self.watched_symbols.remove(symbol)
            if symbol in self.price_cache:
                del self.price_cache[symbol]
            logger.info(f"Removed watched symbol: {symbol}")

# グローバルサービスインスタンス
realtime_service = RealtimeService()