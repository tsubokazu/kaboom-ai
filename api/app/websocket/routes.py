from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from app.websocket.manager import websocket_manager
from app.middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None  # クエリパラメータから認証トークン取得
):
    """
    WebSocketエンドポイント
    フロントエンドのwebsocketStore.tsと互換性のあるプロトコル実装
    """
    connection_id = None
    user_info = None
    
    try:
        # トークンがある場合は認証を試行（オプション）
        if token:
            try:
                # TODO: Supabase JWT検証を実装
                # user_info = await verify_supabase_token(token)
                pass
            except Exception as e:
                logger.warning(f"WebSocket authentication failed: {e}")
                # 認証失敗でも接続は許可（匿名接続）
        
        # WebSocket接続を確立
        connection_id = await websocket_manager.connect(
            websocket,
            user_id=user_info.get("user_id") if user_info else None
        )
        
        logger.info(f"WebSocket connection established: {connection_id}")
        
        # メッセージループ
        while True:
            try:
                # クライアントからメッセージ受信
                message = await websocket.receive_text()
                
                # メッセージをマネージャーで処理
                await websocket_manager.handle_message(connection_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket message loop: {e}")
                break
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    
    finally:
        # 接続をクリーンアップ
        if connection_id:
            await websocket_manager.disconnect(connection_id)

@router.get("/ws/stats")
async def websocket_stats():
    """WebSocket接続統計情報を取得"""
    try:
        stats = websocket_manager.get_connection_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/ws/broadcast")
async def broadcast_message(
    message_type: str,
    payload: dict,
    topic: Optional[str] = None,
    # user = Depends(get_current_user)  # TODO: 管理者権限チェック
):
    """
    管理者用：メッセージをブロードキャスト
    主に開発・デバッグ用途
    """
    try:
        message = {
            "type": message_type,
            "payload": payload
        }
        
        await websocket_manager.broadcast(message, topic)
        
        return JSONResponse(content={
            "success": True,
            "message": "Message broadcasted successfully",
            "topic": topic,
            "active_connections": len(websocket_manager.active_connections)
        })
        
    except Exception as e:
        logger.error(f"Error broadcasting message: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))