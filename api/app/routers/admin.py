# app/routers/admin.py

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import io

from app.services.monitoring_service import monitoring_service
from app.services.reporting_service import (
    reporting_service, ReportType, ReportFormat, 
    PerformanceReport, RiskReport, ComplianceReport
)
from app.middleware.auth import get_current_user
from app.models.user import User
from app.database.connection import AsyncSessionLocal
from sqlalchemy import select, func, and_
from app.models.user import User as UserModel
from app.models.portfolio import Portfolio
from app.models.trading import Order, Trade

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Dashboard"])

# Pydantic Models
class UserStatsRequest(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_inactive: bool = False

class ReportGenerationRequest(BaseModel):
    user_id: Optional[str] = None
    report_type: ReportType
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    format: ReportFormat = ReportFormat.JSON
    include_charts: bool = False

class SystemMaintenanceRequest(BaseModel):
    action: str = Field(..., description="maintenance action: restart, cleanup, backup")
    scheduled_time: Optional[datetime] = None
    notify_users: bool = True

# Admin Authorization Check
def check_admin_permission(current_user: User = Depends(get_current_user)):
    """管理者権限チェック"""
    if not current_user.is_admin:  # User モデルに is_admin フィールドが必要
        raise HTTPException(status_code=403, detail="管理者権限が必要です")
    return current_user

# Dashboard Endpoints
@router.get("/dashboard", response_model=Dict[str, Any])
async def get_admin_dashboard(
    admin_user: User = Depends(check_admin_permission)
):
    """管理ダッシュボード情報取得"""
    try:
        # システムメトリクス取得
        dashboard_data = await monitoring_service.get_dashboard_data()
        
        # ユーザー統計
        async with AsyncSessionLocal() as session:
            # 総ユーザー数
            total_users_result = await session.execute(select(func.count(UserModel.id)))
            total_users = total_users_result.scalar()
            
            # アクティブユーザー数（過去30日）
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            active_users_result = await session.execute(
                select(func.count(UserModel.id)).where(
                    UserModel.last_login_at >= thirty_days_ago
                )
            )
            active_users = active_users_result.scalar()
            
            # プレミアムユーザー数
            premium_users_result = await session.execute(
                select(func.count(UserModel.id)).where(UserModel.is_premium == True)
            )
            premium_users = premium_users_result.scalar()
            
            # 総ポートフォリオ数
            total_portfolios_result = await session.execute(select(func.count(Portfolio.id)))
            total_portfolios = total_portfolios_result.scalar()
            
            # 今日の取引数
            today = datetime.utcnow().date()
            today_trades_result = await session.execute(
                select(func.count(Trade.id)).where(
                    func.date(Trade.trade_date) == today
                )
            )
            today_trades = today_trades_result.scalar()
            
            # 今日の注文数
            today_orders_result = await session.execute(
                select(func.count(Order.id)).where(
                    func.date(Order.created_at) == today
                )
            )
            today_orders = today_orders_result.scalar()
        
        # AI使用統計
        ai_stats = await _get_ai_usage_stats()
        
        return {
            "system_health": dashboard_data,
            "user_statistics": {
                "total_users": total_users,
                "active_users": active_users,
                "premium_users": premium_users,
                "user_growth_rate": await _calculate_user_growth_rate()
            },
            "trading_statistics": {
                "total_portfolios": total_portfolios,
                "today_trades": today_trades,
                "today_orders": today_orders,
                "total_volume_today": await _get_total_volume_today()
            },
            "ai_statistics": ai_stats,
            "system_alerts": dashboard_data.get("active_alerts", []),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Dashboard data retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="ダッシュボードデータの取得でエラーが発生しました")

@router.get("/users", response_model=Dict[str, Any])
async def get_user_management(
    page: int = Query(1, ge=1, description="ページ番号"),
    per_page: int = Query(50, ge=1, le=100, description="1ページあたりの件数"),
    search: Optional[str] = Query(None, description="検索キーワード"),
    status: Optional[str] = Query(None, description="ステータスフィルター"),
    admin_user: User = Depends(check_admin_permission)
):
    """ユーザー管理情報取得"""
    try:
        offset = (page - 1) * per_page
        
        async with AsyncSessionLocal() as session:
            # ベースクエリ
            query = select(UserModel)
            
            # 検索フィルター
            if search:
                query = query.where(
                    or_(
                        UserModel.email.ilike(f"%{search}%"),
                        UserModel.full_name.ilike(f"%{search}%"),
                        UserModel.display_name.ilike(f"%{search}%")
                    )
                )
            
            # ステータスフィルター
            if status == "active":
                query = query.where(UserModel.is_active == True)
            elif status == "inactive":
                query = query.where(UserModel.is_active == False)
            elif status == "premium":
                query = query.where(UserModel.is_premium == True)
            
            # 総件数取得
            count_query = select(func.count(UserModel.id))
            if search:
                count_query = count_query.where(
                    or_(
                        UserModel.email.ilike(f"%{search}%"),
                        UserModel.full_name.ilike(f"%{search}%"),
                        UserModel.display_name.ilike(f"%{search}%")
                    )
                )
            
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()
            
            # ページング適用
            query = query.offset(offset).limit(per_page).order_by(UserModel.created_at.desc())
            
            # ユーザー取得
            result = await session.execute(query)
            users = result.scalars().all()
            
            # 各ユーザーの詳細情報を取得
            user_data = []
            for user in users:
                # ユーザーのポートフォリオ数取得
                portfolio_count_result = await session.execute(
                    select(func.count(Portfolio.id)).where(Portfolio.user_id == user.id)
                )
                portfolio_count = portfolio_count_result.scalar()
                
                # 最新の取引日
                latest_trade_result = await session.execute(
                    select(func.max(Trade.trade_date)).where(Trade.user_id == user.id)
                )
                latest_trade = latest_trade_result.scalar()
                
                user_data.append({
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "display_name": user.display_name,
                    "is_active": user.is_active,
                    "is_premium": user.is_premium,
                    "is_verified": user.is_verified,
                    "portfolio_count": portfolio_count,
                    "last_login": user.last_login_at.isoformat() if user.last_login_at else None,
                    "latest_trade": latest_trade.isoformat() if latest_trade else None,
                    "created_at": user.created_at.isoformat(),
                    "risk_tolerance": user.risk_tolerance
                })
        
        return {
            "users": user_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_count,
                "pages": (total_count + per_page - 1) // per_page
            },
            "filters": {
                "search": search,
                "status": status
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"User management data failed: {e}")
        raise HTTPException(status_code=500, detail="ユーザー管理データの取得でエラーが発生しました")

@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool = Query(..., description="ユーザーの有効/無効状態"),
    admin_user: User = Depends(check_admin_permission)
):
    """ユーザーステータス更新"""
    try:
        async with AsyncSessionLocal() as session:
            user_query = select(UserModel).where(UserModel.id == user_id)
            result = await session.execute(user_query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
            
            user.is_active = is_active
            user.updated_at = datetime.utcnow()
            
            await session.commit()
            
            logger.info(f"User {user_id} status updated to {is_active} by admin {admin_user.id}")
            
            return {
                "user_id": user_id,
                "is_active": is_active,
                "updated_by": str(admin_user.id),
                "updated_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"User status update failed: {e}")
        raise HTTPException(status_code=500, detail="ユーザーステータスの更新でエラーが発生しました")

@router.post("/reports/generate", response_model=Dict[str, Any])
async def generate_admin_report(
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks,
    admin_user: User = Depends(check_admin_permission)
):
    """管理レポート生成"""
    try:
        # 期間設定
        end_date = request.end_date or datetime.utcnow()
        if request.start_date:
            start_date = request.start_date
        else:
            if request.report_type == ReportType.DAILY:
                start_date = end_date - timedelta(days=1)
            elif request.report_type == ReportType.WEEKLY:
                start_date = end_date - timedelta(weeks=1)
            elif request.report_type == ReportType.MONTHLY:
                start_date = end_date - timedelta(days=30)
            elif request.report_type == ReportType.QUARTERLY:
                start_date = end_date - timedelta(days=90)
            elif request.report_type == ReportType.ANNUAL:
                start_date = end_date - timedelta(days=365)
            else:
                start_date = end_date - timedelta(days=30)
        
        report_id = f"admin_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # バックグラウンドでレポート生成
        background_tasks.add_task(
            _generate_admin_report_background,
            report_id,
            request,
            start_date,
            end_date,
            admin_user.id
        )
        
        return {
            "report_id": report_id,
            "status": "generating",
            "report_type": request.report_type,
            "format": request.format,
            "estimated_completion": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
            "message": "レポート生成を開始しました。完了次第通知されます。"
        }
        
    except Exception as e:
        logger.error(f"Report generation request failed: {e}")
        raise HTTPException(status_code=500, detail="レポート生成リクエストでエラーが発生しました")

@router.get("/reports/{report_id}/download")
async def download_admin_report(
    report_id: str,
    admin_user: User = Depends(check_admin_permission)
):
    """管理レポートダウンロード"""
    try:
        # Redis からレポートデータ取得
        from app.services.redis_client import redis_client
        report_data = await redis_client.get(f"admin_report:{report_id}")
        
        if not report_data:
            raise HTTPException(status_code=404, detail="レポートが見つかりません")
        
        import json
        report_info = json.loads(report_data)
        
        if report_info.get("status") != "completed":
            raise HTTPException(status_code=202, detail="レポートがまだ生成中です")
        
        # ファイルデータ取得
        file_data = await redis_client.get(f"admin_report_file:{report_id}")
        if not file_data:
            raise HTTPException(status_code=404, detail="レポートファイルが見つかりません")
        
        import base64
        file_content = base64.b64decode(file_data)
        
        # レスポンス
        media_type = report_info.get("media_type", "application/octet-stream")
        filename = report_info.get("filename", f"{report_id}.json")
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Report download failed: {e}")
        raise HTTPException(status_code=500, detail="レポートダウンロードでエラーが発生しました")

@router.post("/maintenance", response_model=Dict[str, Any])
async def system_maintenance(
    request: SystemMaintenanceRequest,
    background_tasks: BackgroundTasks,
    admin_user: User = Depends(check_admin_permission)
):
    """システムメンテナンス実行"""
    try:
        maintenance_id = f"maintenance_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        if request.action == "restart":
            # システム再起動（実装要）
            background_tasks.add_task(_system_restart, maintenance_id, admin_user.id)
            message = "システム再起動を開始します"
            
        elif request.action == "cleanup":
            # データクリーンアップ
            background_tasks.add_task(_data_cleanup, maintenance_id, admin_user.id)
            message = "データクリーンアップを開始します"
            
        elif request.action == "backup":
            # データベースバックアップ
            background_tasks.add_task(_database_backup, maintenance_id, admin_user.id)
            message = "データベースバックアップを開始します"
            
        else:
            raise HTTPException(status_code=400, detail="無効なメンテナンス操作です")
        
        return {
            "maintenance_id": maintenance_id,
            "action": request.action,
            "status": "started",
            "scheduled_time": request.scheduled_time.isoformat() if request.scheduled_time else "immediate",
            "initiated_by": str(admin_user.id),
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Maintenance request failed: {e}")
        raise HTTPException(status_code=500, detail="メンテナンス実行でエラーが発生しました")

@router.get("/audit-log", response_model=Dict[str, Any])
async def get_audit_log(
    start_date: Optional[datetime] = Query(None, description="開始日時"),
    end_date: Optional[datetime] = Query(None, description="終了日時"),
    user_id: Optional[str] = Query(None, description="ユーザーID"),
    action_type: Optional[str] = Query(None, description="アクションタイプ"),
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=1000),
    admin_user: User = Depends(check_admin_permission)
):
    """監査ログ取得"""
    try:
        # デフォルト期間（過去7日間）
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=7)
        
        # Redis から監査ログ取得
        # 実際の実装では専用の監査ログシステムを使用
        audit_logs = await _get_audit_logs(start_date, end_date, user_id, action_type)
        
        # ページング処理
        offset = (page - 1) * per_page
        paginated_logs = audit_logs[offset:offset + per_page]
        
        return {
            "logs": paginated_logs,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": len(audit_logs),
                "pages": (len(audit_logs) + per_page - 1) // per_page
            },
            "filters": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "user_id": user_id,
                "action_type": action_type
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Audit log retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="監査ログの取得でエラーが発生しました")

# Helper Functions
async def _get_ai_usage_stats() -> Dict[str, Any]:
    """AI使用統計取得"""
    try:
        from app.services.redis_client import redis_client
        
        # 今日のAI使用量
        today_key = f"ai_requests:{datetime.utcnow().strftime('%Y%m%d')}"
        today_requests = await redis_client.get(today_key) or "0"
        
        # 今月のAI使用量
        month_key = f"ai_requests_monthly:{datetime.utcnow().strftime('%Y%m')}"
        month_requests = await redis_client.get(month_key) or "0"
        
        # AIコスト
        cost_key = f"ai_cost_monthly:{datetime.utcnow().strftime('%Y%m')}"
        month_cost = await redis_client.get(cost_key) or "0"
        
        return {
            "today_requests": int(today_requests),
            "month_requests": int(month_requests),
            "month_cost": float(month_cost),
            "top_models": [
                {"model": "gpt-4-turbo", "requests": 150, "cost": 25.50},
                {"model": "claude-3-sonnet", "requests": 120, "cost": 18.75},
                {"model": "gemini-pro", "requests": 80, "cost": 12.30}
            ]
        }
    except:
        return {
            "today_requests": 0,
            "month_requests": 0,
            "month_cost": 0.0,
            "top_models": []
        }

async def _calculate_user_growth_rate() -> float:
    """ユーザー増加率計算"""
    try:
        async with AsyncSessionLocal() as session:
            # 先月のユーザー数
            last_month = datetime.utcnow() - timedelta(days=30)
            last_month_users = await session.execute(
                select(func.count(UserModel.id)).where(UserModel.created_at <= last_month)
            )
            last_month_count = last_month_users.scalar()
            
            # 今月のユーザー数
            current_users = await session.execute(select(func.count(UserModel.id)))
            current_count = current_users.scalar()
            
            if last_month_count > 0:
                growth_rate = ((current_count - last_month_count) / last_month_count) * 100
                return round(growth_rate, 2)
    except:
        pass
    
    return 0.0

async def _get_total_volume_today() -> float:
    """今日の総取引量取得"""
    try:
        today = datetime.utcnow().date()
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(func.sum(Trade.total_amount)).where(
                    func.date(Trade.trade_date) == today
                )
            )
            total_volume = result.scalar() or 0
            return float(total_volume)
    except:
        return 0.0

async def _generate_admin_report_background(
    report_id: str,
    request: ReportGenerationRequest,
    start_date: datetime,
    end_date: datetime,
    admin_user_id: str
):
    """バックグラウンドでレポート生成"""
    try:
        from app.services.redis_client import redis_client
        
        # ステータス更新
        await redis_client.set(
            f"admin_report:{report_id}",
            json.dumps({"status": "processing", "progress": 0}),
            expire=3600
        )
        
        # システム全体のパフォーマンスレポート生成
        if request.user_id:
            report = await reporting_service.generate_performance_report(
                request.user_id, start_date, end_date
            )
        else:
            # 全ユーザーの集計レポート
            report = await _generate_system_wide_report(start_date, end_date)
        
        # レポートをエクスポート
        file_data, media_type = await reporting_service.export_report(report, request.format)
        
        # ファイルをRedisに保存
        import base64
        file_base64 = base64.b64encode(file_data).decode('utf-8')
        await redis_client.set(f"admin_report_file:{report_id}", file_base64, expire=3600)
        
        # 完了ステータス更新
        filename = f"{report_id}.{request.format.value}"
        await redis_client.set(
            f"admin_report:{report_id}",
            json.dumps({
                "status": "completed",
                "filename": filename,
                "media_type": media_type,
                "generated_by": admin_user_id,
                "generated_at": datetime.utcnow().isoformat()
            }),
            expire=3600
        )
        
    except Exception as e:
        logger.error(f"Background report generation failed: {e}")
        await redis_client.set(
            f"admin_report:{report_id}",
            json.dumps({"status": "failed", "error": str(e)}),
            expire=3600
        )

async def _generate_system_wide_report(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """システム全体のレポート生成"""
    # システム全体の統計を生成
    async with get_async_session() as session:
        # 総取引数・取引量
        total_trades_result = await session.execute(
            select(func.count(Trade.id), func.sum(Trade.total_amount)).where(
                and_(Trade.trade_date >= start_date, Trade.trade_date <= end_date)
            )
        )
        total_trades, total_volume = total_trades_result.fetchone()
        
        # ユーザー統計
        active_users_result = await session.execute(
            select(func.count(UserModel.id.distinct())).select_from(
                UserModel.__table__.join(Trade.__table__, UserModel.id == Trade.user_id)
            ).where(Trade.trade_date >= start_date)
        )
        active_users = active_users_result.scalar()
    
    return {
        "report_type": "system_wide",
        "period": {"start": start_date, "end": end_date},
        "trading_stats": {
            "total_trades": total_trades or 0,
            "total_volume": float(total_volume or 0),
            "active_users": active_users or 0
        },
        "generated_at": datetime.utcnow()
    }

async def _system_restart(maintenance_id: str, admin_user_id: str):
    """システム再起動処理"""
    # 実際の実装では安全な再起動プロセスを実行
    logger.info(f"System restart initiated by admin {admin_user_id}")
    # TODO: 実装

async def _data_cleanup(maintenance_id: str, admin_user_id: str):
    """データクリーンアップ処理"""
    logger.info(f"Data cleanup initiated by admin {admin_user_id}")
    # TODO: 古いログ・キャッシュデータの削除

async def _database_backup(maintenance_id: str, admin_user_id: str):
    """データベースバックアップ処理"""
    logger.info(f"Database backup initiated by admin {admin_user_id}")
    # TODO: データベースバックアップ実行

async def _get_audit_logs(
    start_date: datetime,
    end_date: datetime,
    user_id: Optional[str],
    action_type: Optional[str]
) -> List[Dict[str, Any]]:
    """監査ログ取得"""
    # 実際の実装では専用の監査システムから取得
    return [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": "sample_user_id",
            "action": "login",
            "resource": "system",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0..."
        }
    ]