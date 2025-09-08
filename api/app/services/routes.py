from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List, Optional
import logging

from app.services.realtime_service import realtime_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Data Services"])

@router.get("/prices")
async def get_current_prices():
    """現在の価格データを取得"""
    try:
        prices = realtime_service.get_current_prices()
        return JSONResponse(content={
            "success": True,
            "data": prices,
            "count": len(prices)
        })
    except Exception as e:
        logger.error(f"Error getting current prices: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/prices/{symbol}")
async def get_symbol_price(symbol: str):
    """特定銘柄の価格データを取得"""
    try:
        prices = realtime_service.get_current_prices()
        
        if symbol not in prices:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Price data not found for symbol: {symbol}"
            )
        
        return JSONResponse(content={
            "success": True,
            "data": prices[symbol]
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting price for {symbol}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/analysis/{symbol}")
async def trigger_ai_analysis(
    symbol: str,
    analysis_type: str = "technical"
):
    """AI分析をトリガー"""
    try:
        result = await realtime_service.trigger_ai_analysis(symbol, analysis_type)
        
        return JSONResponse(content={
            "success": True,
            "message": f"AI analysis triggered for {symbol}",
            "analysis_id": result.get("generated_at"),
            "data": result
        })
    except Exception as e:
        logger.error(f"Error triggering AI analysis for {symbol}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/watchlist/add")
async def add_watched_symbol(symbol: str):
    """監視銘柄を追加"""
    try:
        realtime_service.add_watched_symbol(symbol)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Added {symbol} to watchlist",
            "watchlist": realtime_service.watched_symbols
        })
    except Exception as e:
        logger.error(f"Error adding symbol {symbol}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/watchlist/remove")
async def remove_watched_symbol(symbol: str):
    """監視銘柄を削除"""
    try:
        realtime_service.remove_watched_symbol(symbol)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Removed {symbol} from watchlist",
            "watchlist": realtime_service.watched_symbols
        })
    except Exception as e:
        logger.error(f"Error removing symbol {symbol}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/watchlist")
async def get_watchlist():
    """監視銘柄一覧を取得"""
    try:
        return JSONResponse(content={
            "success": True,
            "data": realtime_service.watched_symbols,
            "count": len(realtime_service.watched_symbols)
        })
    except Exception as e:
        logger.error(f"Error getting watchlist: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))