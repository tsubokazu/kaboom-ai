# app/services/reporting_service.py

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json
import io
import base64

from app.services.redis_client import redis_client
from app.database.connection import AsyncSessionLocal
from app.models.portfolio import Portfolio, Holding
from app.models.trading import Order, Trade
from app.models.user import User
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

class ReportType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"  
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"

class ReportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    EXCEL = "excel"

@dataclass
class PerformanceReport:
    """パフォーマンスレポート"""
    user_id: str
    period_start: datetime
    period_end: datetime
    total_return: float
    total_return_percent: float
    realized_pnl: float
    unrealized_pnl: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    average_gain: float
    average_loss: float
    max_gain: float
    max_loss: float
    sharpe_ratio: Optional[float]
    max_drawdown: float
    portfolio_value_start: float
    portfolio_value_end: float
    benchmark_return: float
    alpha: float
    beta: float
    top_performers: List[Dict[str, Any]]
    worst_performers: List[Dict[str, Any]]
    trading_summary: Dict[str, Any]

@dataclass
class RiskReport:
    """リスクレポート"""
    user_id: str
    portfolio_id: str
    var_95: float
    var_99: float
    expected_shortfall: float
    volatility: float
    beta: float
    correlation_matrix: Dict[str, Dict[str, float]]
    sector_allocation: Dict[str, float]
    concentration_risk: Dict[str, float]
    currency_exposure: Dict[str, float]
    risk_recommendations: List[str]

@dataclass 
class ComplianceReport:
    """コンプライアンスレポート"""
    user_id: str
    period: str
    total_transactions: int
    suspicious_activities: List[Dict[str, Any]]
    risk_violations: List[Dict[str, Any]]
    regulatory_alerts: List[Dict[str, Any]]
    audit_trail: List[Dict[str, Any]]
    compliance_score: float

class ReportingService:
    """レポート生成サービス"""
    
    def __init__(self):
        self.report_cache = {}
        
    async def generate_performance_report(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        portfolio_ids: Optional[List[str]] = None
    ) -> PerformanceReport:
        """パフォーマンスレポート生成"""
        
        async with AsyncSessionLocal() as session:
            # ユーザーのポートフォリオ取得
            if portfolio_ids:
                portfolio_query = select(Portfolio).where(
                    and_(Portfolio.user_id == user_id, Portfolio.id.in_(portfolio_ids))
                ).options(selectinload(Portfolio.holdings))
            else:
                portfolio_query = select(Portfolio).where(
                    Portfolio.user_id == user_id
                ).options(selectinload(Portfolio.holdings))
            
            portfolios = (await session.execute(portfolio_query)).scalars().all()
            
            if not portfolios:
                raise ValueError("ポートフォリオが見つかりません")
            
            # 取引履歴取得
            trades_query = select(Trade).where(
                and_(
                    Trade.user_id == user_id,
                    Trade.trade_date >= start_date,
                    Trade.trade_date <= end_date
                )
            )
            trades = (await session.execute(trades_query)).scalars().all()
            
            # パフォーマンス計算
            total_return = sum(p.total_return or 0 for p in portfolios)
            total_value_start = sum(p.initial_capital for p in portfolios)
            total_value_end = sum(p.total_value for p in portfolios)
            
            total_return_percent = ((total_value_end - total_value_start) / total_value_start * 100) if total_value_start > 0 else 0
            
            # 取引統計
            winning_trades = len([t for t in trades if (t.realized_pnl or 0) > 0])
            losing_trades = len([t for t in trades if (t.realized_pnl or 0) < 0])
            total_trades = len(trades)
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # 損益統計
            gains = [t.realized_pnl for t in trades if (t.realized_pnl or 0) > 0]
            losses = [abs(t.realized_pnl) for t in trades if (t.realized_pnl or 0) < 0]
            
            average_gain = sum(gains) / len(gains) if gains else 0
            average_loss = sum(losses) / len(losses) if losses else 0
            max_gain = max(gains) if gains else 0
            max_loss = max(losses) if losses else 0
            
            # 各ポートフォリオのパフォーマンス
            portfolio_performance = []
            for portfolio in portfolios:
                portfolio_trades = [t for t in trades if t.portfolio_id == portfolio.id]
                portfolio_return = sum(t.realized_pnl or 0 for t in portfolio_trades)
                
                portfolio_performance.append({
                    "portfolio_id": str(portfolio.id),
                    "portfolio_name": portfolio.name,
                    "return": portfolio_return,
                    "return_percent": (portfolio.total_return or 0) * 100,
                    "trades_count": len(portfolio_trades)
                })
            
            # 銘柄別パフォーマンス
            symbol_performance = {}
            for trade in trades:
                symbol = trade.symbol
                if symbol not in symbol_performance:
                    symbol_performance[symbol] = {
                        "symbol": symbol,
                        "total_pnl": 0,
                        "trades_count": 0,
                        "quantity": 0
                    }
                
                symbol_performance[symbol]["total_pnl"] += trade.realized_pnl or 0
                symbol_performance[symbol]["trades_count"] += 1
                symbol_performance[symbol]["quantity"] += trade.quantity if trade.side == "buy" else -trade.quantity
            
            # トップ・ワーストパフォーマー
            symbol_list = list(symbol_performance.values())
            top_performers = sorted(symbol_list, key=lambda x: x["total_pnl"], reverse=True)[:5]
            worst_performers = sorted(symbol_list, key=lambda x: x["total_pnl"])[:5]
            
            # ベンチマーク・リスク指標（簡易計算）
            benchmark_return = 5.0  # TODO: 実際のベンチマーク取得
            sharpe_ratio = await self._calculate_sharpe_ratio(portfolios, trades)
            max_drawdown = max((p.max_drawdown or 0) for p in portfolios)
            beta = sum(p.beta or 1.0 for p in portfolios) / len(portfolios) if portfolios else 1.0
            alpha = total_return_percent - (benchmark_return * beta)
            
            return PerformanceReport(
                user_id=user_id,
                period_start=start_date,
                period_end=end_date,
                total_return=total_return,
                total_return_percent=total_return_percent,
                realized_pnl=sum(t.realized_pnl or 0 for t in trades),
                unrealized_pnl=sum(p.unrealized_pnl or 0 for p in portfolios),
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                average_gain=average_gain,
                average_loss=average_loss,
                max_gain=max_gain,
                max_loss=max_loss,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                portfolio_value_start=total_value_start,
                portfolio_value_end=total_value_end,
                benchmark_return=benchmark_return,
                alpha=alpha,
                beta=beta,
                top_performers=top_performers,
                worst_performers=worst_performers,
                trading_summary={
                    "portfolios": portfolio_performance,
                    "total_commission": sum(t.commission or 0 for t in trades),
                    "total_fees": sum(t.fees or 0 for t in trades)
                }
            )
    
    async def generate_risk_report(
        self,
        user_id: str,
        portfolio_id: str
    ) -> RiskReport:
        """リスクレポート生成"""
        
        async with AsyncSessionLocal() as session:
            # ポートフォリオとホールディング取得
            portfolio_query = select(Portfolio).where(
                and_(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
            ).options(selectinload(Portfolio.holdings))
            
            result = await session.execute(portfolio_query)
            portfolio = result.scalar_one_or_none()
            
            if not portfolio:
                raise ValueError("ポートフォリオが見つかりません")
            
            holdings = portfolio.holdings
            
            # VaR計算（簡易版）
            var_95 = await self._calculate_var(holdings, confidence=0.95)
            var_99 = await self._calculate_var(holdings, confidence=0.99)
            expected_shortfall = var_95 * 1.3  # 簡易計算
            
            # ボラティリティ計算
            volatility = portfolio.volatility or 0.0
            beta = portfolio.beta or 1.0
            
            # セクター分散
            sector_allocation = {}
            total_value = sum(h.market_value for h in holdings)
            
            for holding in holdings:
                sector = holding.sector or "その他"
                if sector not in sector_allocation:
                    sector_allocation[sector] = 0
                sector_allocation[sector] += (holding.market_value / total_value * 100) if total_value > 0 else 0
            
            # 集中リスク
            concentration_risk = {}
            for holding in holdings:
                weight = (holding.market_value / total_value * 100) if total_value > 0 else 0
                if weight > 10:  # 10%以上の集中
                    concentration_risk[holding.symbol] = weight
            
            # 相関行列（簡易版）
            correlation_matrix = await self._calculate_correlation_matrix(holdings)
            
            # 通貨エクスポージャー
            currency_exposure = {"JPY": 100.0}  # TODO: 実際の通貨分散計算
            
            # リスク推奨事項
            risk_recommendations = self._generate_risk_recommendations(
                sector_allocation, concentration_risk, volatility
            )
            
            return RiskReport(
                user_id=user_id,
                portfolio_id=portfolio_id,
                var_95=var_95,
                var_99=var_99,
                expected_shortfall=expected_shortfall,
                volatility=volatility,
                beta=beta,
                correlation_matrix=correlation_matrix,
                sector_allocation=sector_allocation,
                concentration_risk=concentration_risk,
                currency_exposure=currency_exposure,
                risk_recommendations=risk_recommendations
            )
    
    async def generate_compliance_report(
        self,
        user_id: str,
        period: str
    ) -> ComplianceReport:
        """コンプライアンスレポート生成"""
        
        # 期間設定
        end_date = datetime.utcnow()
        if period == "monthly":
            start_date = end_date - timedelta(days=30)
        elif period == "quarterly":
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)
        
        async with AsyncSessionLocal() as session:
            # 取引履歴取得
            trades_query = select(Trade).where(
                and_(
                    Trade.user_id == user_id,
                    Trade.trade_date >= start_date,
                    Trade.trade_date <= end_date
                )
            )
            trades = (await session.execute(trades_query)).scalars().all()
            
            # 注文履歴取得
            orders_query = select(Order).where(
                and_(
                    Order.user_id == user_id,
                    Order.created_at >= start_date,
                    Order.created_at <= end_date
                )
            )
            orders = (await session.execute(orders_query)).scalars().all()
            
            # 疑わしい活動チェック
            suspicious_activities = self._detect_suspicious_activities(trades, orders)
            
            # リスク違反チェック
            risk_violations = await self._check_risk_violations(user_id, trades)
            
            # 規制アラート
            regulatory_alerts = self._check_regulatory_compliance(trades)
            
            # 監査証跡
            audit_trail = [
                {
                    "timestamp": t.trade_date.isoformat(),
                    "action": f"{t.side.upper()} {t.quantity} {t.symbol}",
                    "amount": float(t.total_amount),
                    "trade_id": str(t.id)
                }
                for t in trades
            ]
            
            # コンプライアンススコア計算
            compliance_score = self._calculate_compliance_score(
                suspicious_activities, risk_violations, regulatory_alerts
            )
            
            return ComplianceReport(
                user_id=user_id,
                period=period,
                total_transactions=len(trades),
                suspicious_activities=suspicious_activities,
                risk_violations=risk_violations,
                regulatory_alerts=regulatory_alerts,
                audit_trail=audit_trail,
                compliance_score=compliance_score
            )
    
    async def export_report(
        self,
        report: Any,
        format: ReportFormat
    ) -> Tuple[bytes, str]:
        """レポートエクスポート"""
        
        if format == ReportFormat.JSON:
            return await self._export_json(report)
        elif format == ReportFormat.CSV:
            return await self._export_csv(report)
        elif format == ReportFormat.PDF:
            return await self._export_pdf(report)
        elif format == ReportFormat.EXCEL:
            return await self._export_excel(report)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def _export_json(self, report: Any) -> Tuple[bytes, str]:
        """JSON形式でエクスポート"""
        if hasattr(report, '__dict__'):
            data = report.__dict__
        else:
            data = report
        
        # datetime オブジェクトを文字列に変換
        json_str = json.dumps(data, default=str, ensure_ascii=False, indent=2)
        return json_str.encode('utf-8'), "application/json"
    
    async def _export_csv(self, report: Any) -> Tuple[bytes, str]:
        """CSV形式でエクスポート"""
        import csv
        
        output = io.StringIO()
        
        if isinstance(report, PerformanceReport):
            writer = csv.writer(output)
            writer.writerow(["項目", "値"])
            writer.writerow(["期間開始", report.period_start])
            writer.writerow(["期間終了", report.period_end])
            writer.writerow(["総リターン", f"{report.total_return_percent:.2f}%"])
            writer.writerow(["実現損益", f"¥{report.realized_pnl:,.0f}"])
            writer.writerow(["未実現損益", f"¥{report.unrealized_pnl:,.0f}"])
            writer.writerow(["総取引数", report.total_trades])
            writer.writerow(["勝率", f"{report.win_rate:.1f}%"])
            writer.writerow(["最大利益", f"¥{report.max_gain:,.0f}"])
            writer.writerow(["最大損失", f"¥{report.max_loss:,.0f}"])
        
        return output.getvalue().encode('utf-8'), "text/csv"
    
    async def _export_pdf(self, report: Any) -> Tuple[bytes, str]:
        """PDF形式でエクスポート"""
        # PDF生成は外部ライブラリが必要
        # ここでは簡易実装
        content = f"レポート生成日: {datetime.utcnow()}\n\n"
        
        if isinstance(report, PerformanceReport):
            content += f"パフォーマンスレポート\n"
            content += f"期間: {report.period_start} - {report.period_end}\n"
            content += f"総リターン: {report.total_return_percent:.2f}%\n"
            content += f"勝率: {report.win_rate:.1f}%\n"
        
        return content.encode('utf-8'), "application/pdf"
    
    async def _export_excel(self, report: Any) -> Tuple[bytes, str]:
        """Excel形式でエクスポート"""
        # Excel生成は外部ライブラリが必要
        # ここでは簡易CSV形式で代用
        return await self._export_csv(report)
    
    # ヘルパーメソッド
    async def _calculate_sharpe_ratio(self, portfolios: List[Portfolio], trades: List[Trade]) -> Optional[float]:
        """シャープレシオ計算"""
        if not trades:
            return None
        
        # 簡易計算
        returns = [t.realized_pnl_percent or 0 for t in trades if t.realized_pnl_percent is not None]
        if len(returns) < 2:
            return None
        
        import statistics
        avg_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        risk_free_rate = 0.1  # 1%のリスクフリーレート
        
        return (avg_return - risk_free_rate) / std_return if std_return > 0 else None
    
    async def _calculate_var(self, holdings: List[Holding], confidence: float) -> float:
        """VaR計算"""
        if not holdings:
            return 0.0
        
        # 簡易VaR計算（正規分布仮定）
        total_value = sum(h.market_value for h in holdings)
        volatility = 0.2  # 20%のボラティリティ仮定
        
        from scipy.stats import norm
        z_score = norm.ppf(1 - confidence)
        var = total_value * volatility * abs(z_score)
        
        return var
    
    async def _calculate_correlation_matrix(self, holdings: List[Holding]) -> Dict[str, Dict[str, float]]:
        """相関行列計算"""
        symbols = [h.symbol for h in holdings]
        
        # 簡易相関行列（実際は価格データから計算）
        correlation_matrix = {}
        for symbol1 in symbols:
            correlation_matrix[symbol1] = {}
            for symbol2 in symbols:
                if symbol1 == symbol2:
                    correlation_matrix[symbol1][symbol2] = 1.0
                else:
                    correlation_matrix[symbol1][symbol2] = 0.3  # 仮の相関係数
        
        return correlation_matrix
    
    def _generate_risk_recommendations(
        self,
        sector_allocation: Dict[str, float],
        concentration_risk: Dict[str, float],
        volatility: float
    ) -> List[str]:
        """リスク推奨事項生成"""
        recommendations = []
        
        # セクター集中リスク
        for sector, allocation in sector_allocation.items():
            if allocation > 50:
                recommendations.append(f"{sector}セクターの集中度が高い（{allocation:.1f}%）- 分散を検討")
        
        # 個別銘柄集中リスク
        for symbol, weight in concentration_risk.items():
            if weight > 20:
                recommendations.append(f"{symbol}の比重が高い（{weight:.1f}%）- ポジション縮小を検討")
        
        # ボラティリティ
        if volatility > 0.3:
            recommendations.append("ポートフォリオのボラティリティが高い - 安定銘柄の追加を検討")
        
        if not recommendations:
            recommendations.append("現在の分散状況は適切です")
        
        return recommendations
    
    def _detect_suspicious_activities(self, trades: List[Trade], orders: List[Order]) -> List[Dict[str, Any]]:
        """疑わしい活動検出"""
        suspicious = []
        
        # 短時間での大量取引
        trade_times = {}
        for trade in trades:
            hour = trade.trade_date.replace(minute=0, second=0, microsecond=0)
            if hour not in trade_times:
                trade_times[hour] = []
            trade_times[hour].append(trade)
        
        for hour, hour_trades in trade_times.items():
            if len(hour_trades) > 10:
                suspicious.append({
                    "type": "high_frequency_trading",
                    "description": f"1時間内に{len(hour_trades)}回の取引",
                    "timestamp": hour.isoformat(),
                    "severity": "medium"
                })
        
        # 異常に大きな取引
        for trade in trades:
            if trade.total_amount > 10000000:  # 1000万円以上
                suspicious.append({
                    "type": "large_transaction",
                    "description": f"大額取引: ¥{trade.total_amount:,.0f}",
                    "timestamp": trade.trade_date.isoformat(),
                    "symbol": trade.symbol,
                    "severity": "high"
                })
        
        return suspicious
    
    async def _check_risk_violations(self, user_id: str, trades: List[Trade]) -> List[Dict[str, Any]]:
        """リスク違反チェック"""
        violations = []
        
        # 取引限度額チェック
        daily_volume = {}
        for trade in trades:
            date = trade.trade_date.date()
            if date not in daily_volume:
                daily_volume[date] = 0
            daily_volume[date] += trade.total_amount
        
        for date, volume in daily_volume.items():
            if volume > 50000000:  # 5000万円/日の限度
                violations.append({
                    "type": "daily_limit_exceeded",
                    "description": f"日次取引限度額超過: ¥{volume:,.0f}",
                    "date": date.isoformat(),
                    "severity": "high"
                })
        
        return violations
    
    def _check_regulatory_compliance(self, trades: List[Trade]) -> List[Dict[str, Any]]:
        """規制コンプライアンスチェック"""
        alerts = []
        
        # インサイダー取引チェック（簡易）
        symbol_trades = {}
        for trade in trades:
            if trade.symbol not in symbol_trades:
                symbol_trades[trade.symbol] = []
            symbol_trades[trade.symbol].append(trade)
        
        for symbol, symbol_trade_list in symbol_trades.items():
            if len(symbol_trade_list) > 5:  # 同一銘柄の頻繁な取引
                alerts.append({
                    "type": "frequent_trading",
                    "description": f"{symbol}の頻繁な取引: {len(symbol_trade_list)}回",
                    "symbol": symbol,
                    "severity": "medium"
                })
        
        return alerts
    
    def _calculate_compliance_score(
        self,
        suspicious_activities: List[Dict],
        risk_violations: List[Dict],
        regulatory_alerts: List[Dict]
    ) -> float:
        """コンプライアンススコア計算"""
        base_score = 100.0
        
        # 違反による減点
        for activity in suspicious_activities:
            if activity["severity"] == "high":
                base_score -= 20
            elif activity["severity"] == "medium":
                base_score -= 10
            else:
                base_score -= 5
        
        for violation in risk_violations:
            base_score -= 25
        
        for alert in regulatory_alerts:
            base_score -= 15
        
        return max(0.0, min(100.0, base_score))

# グローバルインスタンス
reporting_service = ReportingService()