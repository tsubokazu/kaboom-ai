"""
Enhanced market data service using yfinance.
Provides real-time stock prices, historical data, and technical indicators.
"""

import asyncio
import logging
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.services.redis_client import get_redis_client
from app.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)


class MarketDataService:
    """Enhanced market data service with yfinance integration"""
    
    def __init__(self):
        self.cache_ttl = 60  # Cache TTL in seconds
        self.batch_size = 10  # Number of symbols to fetch in batch
        
    async def get_stock_price(self, symbol: str, force_update: bool = False) -> Dict[str, Any]:
        """Get current stock price with caching"""
        try:
            redis_client = await get_redis_client()
            cache_key = f"stock_price:{symbol}"
            
            # Check cache first unless force update
            if not force_update:
                cached_data = await redis_client.get_cache(cache_key)
                if cached_data and isinstance(cached_data, dict):
                    # Check if data is still fresh (within cache TTL)
                    last_updated = datetime.fromisoformat(cached_data.get('last_updated', '2020-01-01T00:00:00'))
                    if (datetime.utcnow() - last_updated).seconds < self.cache_ttl:
                        return cached_data
            
            # Fetch fresh data from yfinance
            price_data = await self._fetch_stock_data(symbol)
            
            if price_data:
                # Cache the data
                await redis_client.set_cache(cache_key, price_data, expire_seconds=self.cache_ttl)
                
                # Broadcast price update via WebSocket
                await websocket_manager.broadcast_price_update(symbol, price_data)
                
                logger.debug(f"Updated price data for {symbol}")
                return price_data
            else:
                logger.warning(f"No price data available for {symbol}")
                return self._get_fallback_data(symbol)
                
        except Exception as e:
            logger.error(f"Failed to get stock price for {symbol}: {e}")
            return self._get_fallback_data(symbol)
    
    async def get_multiple_stock_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get prices for multiple stocks efficiently"""
        try:
            results = {}
            
            # Process symbols in batches
            for i in range(0, len(symbols), self.batch_size):
                batch_symbols = symbols[i:i + self.batch_size]
                batch_results = await self._fetch_batch_stock_data(batch_symbols)
                results.update(batch_results)
                
                # Small delay between batches to respect rate limits
                if i + self.batch_size < len(symbols):
                    await asyncio.sleep(0.1)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get multiple stock prices: {e}")
            return {}
    
    async def get_historical_data(self, symbol: str, period: str = "1mo", 
                                  interval: str = "1d") -> Dict[str, Any]:
        """Get historical price data"""
        try:
            redis_client = await get_redis_client()
            cache_key = f"historical:{symbol}:{period}:{interval}"
            
            # Check cache (longer TTL for historical data)
            cached_data = await redis_client.get_cache(cache_key)
            if cached_data:
                return cached_data
            
            # Fetch from yfinance
            ticker = yf.Ticker(symbol)
            hist_data = await asyncio.to_thread(
                ticker.history, 
                period=period, 
                interval=interval,
                auto_adjust=True,
                prepost=True
            )
            
            if hist_data.empty:
                logger.warning(f"No historical data for {symbol}")
                return {"error": "No data available"}
            
            # Convert to JSON-serializable format
            historical_data = {
                "symbol": symbol,
                "period": period,
                "interval": interval,
                "data": [],
                "last_updated": datetime.utcnow().isoformat()
            }
            
            for index, row in hist_data.iterrows():
                historical_data["data"].append({
                    "date": index.strftime("%Y-%m-%d"),
                    "timestamp": index.isoformat(),
                    "open": float(row["Open"]) if not pd.isna(row["Open"]) else None,
                    "high": float(row["High"]) if not pd.isna(row["High"]) else None,
                    "low": float(row["Low"]) if not pd.isna(row["Low"]) else None,
                    "close": float(row["Close"]) if not pd.isna(row["Close"]) else None,
                    "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0
                })
            
            # Cache for 1 hour for historical data
            await redis_client.set_cache(cache_key, historical_data, expire_seconds=3600)
            
            return historical_data
            
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            return {"error": str(e)}
    
    async def get_technical_indicators(self, symbol: str, period: str = "3mo") -> Dict[str, Any]:
        """Calculate technical indicators"""
        try:
            # Get historical data
            hist_data = await self.get_historical_data(symbol, period)
            
            if "error" in hist_data:
                return hist_data
            
            # Convert to pandas DataFrame for calculations
            df = pd.DataFrame(hist_data["data"])
            if df.empty:
                return {"error": "No data for calculations"}
            
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['volume'] = pd.to_numeric(df['volume'])
            
            # Calculate technical indicators
            indicators = {
                "symbol": symbol,
                "last_updated": datetime.utcnow().isoformat(),
                "current_price": float(df['close'].iloc[-1]) if len(df) > 0 else None,
            }
            
            # Moving Averages
            if len(df) >= 20:
                indicators["sma_20"] = float(df['close'].rolling(window=20).mean().iloc[-1])
            if len(df) >= 50:
                indicators["sma_50"] = float(df['close'].rolling(window=50).mean().iloc[-1])
            if len(df) >= 200:
                indicators["sma_200"] = float(df['close'].rolling(window=200).mean().iloc[-1])
            
            # RSI
            if len(df) >= 14:
                indicators["rsi"] = self._calculate_rsi(df['close'], 14)
            
            # MACD
            if len(df) >= 26:
                macd_line, signal_line, histogram = self._calculate_macd(df['close'])
                indicators["macd"] = {
                    "line": float(macd_line.iloc[-1]) if len(macd_line) > 0 else None,
                    "signal": float(signal_line.iloc[-1]) if len(signal_line) > 0 else None,
                    "histogram": float(histogram.iloc[-1]) if len(histogram) > 0 else None
                }
            
            # Bollinger Bands
            if len(df) >= 20:
                bb_upper, bb_lower, bb_middle = self._calculate_bollinger_bands(df['close'], 20)
                indicators["bollinger_bands"] = {
                    "upper": float(bb_upper.iloc[-1]),
                    "lower": float(bb_lower.iloc[-1]),
                    "middle": float(bb_middle.iloc[-1])
                }
            
            # Support/Resistance levels (simplified)
            if len(df) >= 20:
                recent_highs = df['high'].tail(20)
                recent_lows = df['low'].tail(20)
                indicators["support_resistance"] = {
                    "resistance": float(recent_highs.max()),
                    "support": float(recent_lows.min()),
                    "pivot": float((recent_highs.max() + recent_lows.min() + df['close'].iloc[-1]) / 3)
                }
            
            return indicators
            
        except Exception as e:
            logger.error(f"Failed to calculate technical indicators for {symbol}: {e}")
            return {"error": str(e)}
    
    async def get_company_info(self, symbol: str) -> Dict[str, Any]:
        """Get company information"""
        try:
            redis_client = await get_redis_client()
            cache_key = f"company_info:{symbol}"
            
            # Check cache (long TTL for company info)
            cached_info = await redis_client.get_cache(cache_key)
            if cached_info:
                return cached_info
            
            ticker = yf.Ticker(symbol)
            info = await asyncio.to_thread(lambda: ticker.info)
            
            # Extract relevant information
            company_info = {
                "symbol": symbol,
                "company_name": info.get("longName", "N/A"),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "currency": info.get("currency", "JPY"),
                "exchange": info.get("exchange", "TSE"),
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Cache for 24 hours
            await redis_client.set_cache(cache_key, company_info, expire_seconds=86400)
            
            return company_info
            
        except Exception as e:
            logger.error(f"Failed to get company info for {symbol}: {e}")
            return {"error": str(e)}
    
    async def _fetch_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch current stock data from yfinance"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get current data
            info = await asyncio.to_thread(lambda: ticker.info)
            
            # Get recent price data
            hist = await asyncio.to_thread(
                ticker.history,
                period="2d",
                interval="1m"
            )
            
            if hist.empty:
                return None
            
            current_price = float(hist['Close'].iloc[-1])
            previous_close = info.get("previousClose", current_price)
            
            if previous_close is None:
                previous_close = current_price
            
            change = current_price - previous_close
            change_percent = (change / previous_close * 100) if previous_close != 0 else 0
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "previous_close": float(previous_close),
                "change": change,
                "change_percent": change_percent,
                "volume": int(hist['Volume'].sum()),
                "high": float(hist['High'].max()),
                "low": float(hist['Low'].min()),
                "open": float(hist['Open'].iloc[0]),
                "last_updated": datetime.utcnow().isoformat(),
                "market_status": self._get_market_status()
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch stock data for {symbol}: {e}")
            return None
    
    async def _fetch_batch_stock_data(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch data for multiple symbols"""
        try:
            results = {}
            
            # Use yfinance download for batch processing
            symbols_str = " ".join(symbols)
            data = await asyncio.to_thread(
                yf.download,
                symbols_str,
                period="2d",
                interval="1d",
                group_by='ticker'
            )
            
            if data.empty:
                return results
            
            for symbol in symbols:
                try:
                    if len(symbols) == 1:
                        # Single symbol case
                        symbol_data = data
                    else:
                        # Multiple symbols case
                        symbol_data = data[symbol]
                    
                    if symbol_data.empty:
                        continue
                    
                    current_price = float(symbol_data['Close'].iloc[-1])
                    previous_close = float(symbol_data['Close'].iloc[-2]) if len(symbol_data) > 1 else current_price
                    
                    change = current_price - previous_close
                    change_percent = (change / previous_close * 100) if previous_close != 0 else 0
                    
                    results[symbol] = {
                        "symbol": symbol,
                        "current_price": current_price,
                        "previous_close": previous_close,
                        "change": change,
                        "change_percent": change_percent,
                        "volume": int(symbol_data['Volume'].iloc[-1]) if not pd.isna(symbol_data['Volume'].iloc[-1]) else 0,
                        "high": float(symbol_data['High'].iloc[-1]),
                        "low": float(symbol_data['Low'].iloc[-1]),
                        "open": float(symbol_data['Open'].iloc[-1]),
                        "last_updated": datetime.utcnow().isoformat(),
                        "market_status": self._get_market_status()
                    }
                    
                except Exception as symbol_error:
                    logger.error(f"Failed to process data for {symbol}: {symbol_error}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch batch stock data: {e}")
            return {}
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, lower_band, sma
    
    def _get_market_status(self) -> str:
        """Get current market status (simplified for TSE)"""
        now = datetime.utcnow()
        jst_hour = (now.hour + 9) % 24  # Convert to JST
        
        # TSE trading hours: 9:00-11:30, 12:30-15:00 JST
        if (9 <= jst_hour < 11) or (jst_hour == 11 and now.minute < 30) or (12 <= jst_hour < 15) or (jst_hour == 12 and now.minute >= 30):
            return "open"
        else:
            return "closed"
    
    def _get_fallback_data(self, symbol: str) -> Dict[str, Any]:
        """Return fallback data when real data is unavailable"""
        return {
            "symbol": symbol,
            "current_price": 1000.0,
            "previous_close": 1000.0,
            "change": 0.0,
            "change_percent": 0.0,
            "volume": 1000000,
            "high": 1050.0,
            "low": 950.0,
            "open": 980.0,
            "last_updated": datetime.utcnow().isoformat(),
            "market_status": "closed",
            "note": "Fallback data - real data unavailable"
        }


# Global instance
market_data_service = MarketDataService()