"""
Trading service for database operations.
Handles all order and trade related database interactions.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, and_, or_, func
from sqlalchemy.orm import selectinload
from uuid import UUID
import uuid
import logging
import random
import string

from app.models.user import User
from app.models.portfolio import Portfolio, Holding
from app.models.trading import Order, Trade, OrderStatus, TradeStatus, OrderSide
from app.services.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class TradingService:
    """Service class for trading operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def generate_order_number(self) -> str:
        """Generate unique order number"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"ORD{timestamp}{random_suffix}"
    
    def generate_trade_number(self) -> str:
        """Generate unique trade number"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"TRD{timestamp}{random_suffix}"
    
    async def create_order(self, user_id: UUID, order_data: Dict[str, Any]) -> Order:
        """Create a new trading order"""
        try:
            # Validate portfolio ownership
            portfolio_id = UUID(order_data["portfolio_id"])
            stmt = select(Portfolio).where(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == user_id
            )
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            
            if not portfolio:
                raise ValueError("Portfolio not found or not owned by user")
            
            # Calculate estimated cost
            quantity = order_data["quantity"]
            if order_data["order_type"] == "market":
                # For market orders, use current market price (placeholder)
                estimated_price = Decimal(str(order_data.get("estimated_price", 1000)))
            else:
                estimated_price = Decimal(str(order_data["limit_price"]))
            
            estimated_cost = quantity * estimated_price
            
            # For buy orders, check if enough cash available
            if order_data["side"] == "buy" and not portfolio.is_paper_trading:
                if portfolio.current_cash < estimated_cost:
                    raise ValueError("Insufficient funds for this order")
            
            # Create order
            order = Order(
                user_id=user_id,
                portfolio_id=portfolio_id,
                order_number=self.generate_order_number(),
                symbol=order_data["symbol"],
                side=order_data["side"],
                order_type=order_data["order_type"],
                quantity=quantity,
                limit_price=Decimal(str(order_data.get("limit_price"))) if order_data.get("limit_price") else None,
                stop_price=Decimal(str(order_data.get("stop_price"))) if order_data.get("stop_price") else None,
                remaining_quantity=quantity,
                estimated_cost=estimated_cost,
                commission=Decimal(str(order_data.get("commission", 0))),
                fees=Decimal(str(order_data.get("fees", 0))),
                time_in_force=order_data.get("time_in_force", "DAY"),
                is_paper_trade=portfolio.is_paper_trading,
                is_ai_generated=order_data.get("is_ai_generated", False),
                ai_strategy=order_data.get("ai_strategy"),
                ai_confidence=Decimal(str(order_data["ai_confidence"])) if order_data.get("ai_confidence") else None,
                notes=order_data.get("notes"),
                order_metadata=order_data.get("metadata", {})
            )
            
            # Set expiry for DAY orders
            if order.time_in_force == "DAY":
                order.expires_at = datetime.utcnow().replace(hour=15, minute=0, second=0, microsecond=0)
                if order.expires_at <= datetime.utcnow():
                    order.expires_at += timedelta(days=1)
            
            self.db.add(order)
            await self.db.commit()
            await self.db.refresh(order)
            
            # Cache order
            redis_client = await get_redis_client()
            await redis_client.set_cache(
                f"order:{order.id}",
                order.to_dict(),
                expire_seconds=3600
            )
            
            logger.info(f"Created order {order.order_number} for user {user_id}")
            return order
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create order: {e}")
            raise
    
    async def get_order(self, order_id: UUID, user_id: UUID) -> Optional[Order]:
        """Get order by ID with user ownership check"""
        try:
            stmt = select(Order).where(
                Order.id == order_id,
                Order.user_id == user_id
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return None
    
    async def get_user_orders(self, user_id: UUID, portfolio_id: Optional[UUID] = None, 
                              limit: int = 50, offset: int = 0) -> List[Order]:
        """Get user orders with optional portfolio filter"""
        try:
            stmt = select(Order).where(Order.user_id == user_id)
            
            if portfolio_id:
                stmt = stmt.where(Order.portfolio_id == portfolio_id)
            
            stmt = stmt.order_by(Order.created_at.desc()).limit(limit).offset(offset)
            
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Failed to get orders for user {user_id}: {e}")
            return []
    
    async def update_order(self, order_id: UUID, user_id: UUID, update_data: Dict[str, Any]) -> Optional[Order]:
        """Update order (limited fields)"""
        try:
            order = await self.get_order(order_id, user_id)
            if not order or order.status not in ["pending", "submitted"]:
                return None
            
            # Only allow certain fields to be updated
            updatable_fields = ["limit_price", "stop_price", "notes", "order_metadata"]
            
            for field, value in update_data.items():
                if field in updatable_fields and value is not None:
                    if field in ["limit_price", "stop_price"]:
                        setattr(order, field, Decimal(str(value)))
                    else:
                        setattr(order, field, value)
            
            order.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(order)
            
            # Update cache
            redis_client = await get_redis_client()
            await redis_client.set_cache(
                f"order:{order_id}",
                order.to_dict(),
                expire_seconds=3600
            )
            
            return order
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update order {order_id}: {e}")
            return None
    
    async def cancel_order(self, order_id: UUID, user_id: UUID) -> bool:
        """Cancel an order"""
        try:
            order = await self.get_order(order_id, user_id)
            if not order or order.status not in ["pending", "submitted", "partially_filled"]:
                return False
            
            order.status = "cancelled"
            order.cancelled_at = datetime.utcnow()
            order.updated_at = datetime.utcnow()
            
            await self.db.commit()
            
            # Update cache
            redis_client = await get_redis_client()
            await redis_client.set_cache(
                f"order:{order_id}",
                order.to_dict(),
                expire_seconds=3600
            )
            
            logger.info(f"Cancelled order {order.order_number}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    async def execute_trade(self, order_id: UUID, execution_data: Dict[str, Any]) -> Optional[Trade]:
        """Execute a trade for an order"""
        try:
            # Get order
            stmt = select(Order).where(Order.id == order_id)
            result = await self.db.execute(stmt)
            order = result.scalar_one_or_none()
            
            if not order or order.status not in ["pending", "submitted", "partially_filled"]:
                return None
            
            # Create trade
            quantity = min(execution_data["quantity"], order.remaining_quantity)
            price = Decimal(str(execution_data["price"]))
            total_amount = quantity * price
            
            trade = Trade(
                user_id=order.user_id,
                portfolio_id=order.portfolio_id,
                order_id=order.id,
                trade_number=self.generate_trade_number(),
                symbol=order.symbol,
                side=order.side,
                quantity=quantity,
                price=price,
                total_amount=total_amount,
                commission=Decimal(str(execution_data.get("commission", 0))),
                fees=Decimal(str(execution_data.get("fees", 0))),
                net_amount=total_amount + Decimal(str(execution_data.get("commission", 0))) + Decimal(str(execution_data.get("fees", 0))),
                is_paper_trade=order.is_paper_trade,
                trade_date=datetime.utcnow(),
                settlement_date=datetime.utcnow() + timedelta(days=2),  # T+2 settlement
                market_price_at_execution=Decimal(str(execution_data.get("market_price", price))),
                bid_price=Decimal(str(execution_data.get("bid_price"))) if execution_data.get("bid_price") else None,
                ask_price=Decimal(str(execution_data.get("ask_price"))) if execution_data.get("ask_price") else None,
                notes=execution_data.get("notes"),
                trade_metadata=execution_data.get("metadata", {})
            )
            
            # Update order
            order.filled_quantity += quantity
            order.remaining_quantity -= quantity
            
            # Calculate weighted average fill price
            if order.filled_quantity > 0:
                if order.average_fill_price:
                    total_filled_value = (order.filled_quantity - quantity) * order.average_fill_price + quantity * price
                    order.average_fill_price = total_filled_value / order.filled_quantity
                else:
                    order.average_fill_price = price
            
            # Update order status
            if order.remaining_quantity == 0:
                order.status = "filled"
                order.filled_at = datetime.utcnow()
                order.actual_cost = order.filled_quantity * order.average_fill_price
            else:
                order.status = "partially_filled"
            
            order.updated_at = datetime.utcnow()
            
            # Update portfolio holdings and cash
            await self._update_portfolio_for_trade(trade)
            
            self.db.add(trade)
            await self.db.commit()
            await self.db.refresh(trade)
            
            logger.info(f"Executed trade {trade.trade_number} for order {order.order_number}")
            return trade
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to execute trade for order {order_id}: {e}")
            return None
    
    async def _update_portfolio_for_trade(self, trade: Trade) -> None:
        """Update portfolio holdings and cash for a trade"""
        try:
            # Get portfolio
            stmt = select(Portfolio).where(Portfolio.id == trade.portfolio_id)
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            
            if not portfolio:
                return
            
            # Get or create holding
            stmt = select(Holding).where(
                and_(
                    Holding.portfolio_id == trade.portfolio_id,
                    Holding.symbol == trade.symbol,
                    Holding.is_active == True
                )
            )
            result = await self.db.execute(stmt)
            holding = result.scalar_one_or_none()
            
            if trade.side == "buy":
                if holding:
                    # Update existing holding
                    old_quantity = holding.quantity
                    old_cost = holding.average_cost
                    new_quantity = trade.quantity
                    new_cost = trade.price
                    
                    total_quantity = old_quantity + new_quantity
                    # Weighted average cost
                    holding.average_cost = ((old_quantity * old_cost) + (new_quantity * new_cost)) / total_quantity
                    holding.quantity = total_quantity
                    holding.total_cost = holding.average_cost * holding.quantity
                    holding.current_price = trade.price
                    holding.market_value = holding.current_price * holding.quantity
                    holding.updated_at = datetime.utcnow()
                else:
                    # Create new holding
                    holding = Holding(
                        portfolio_id=trade.portfolio_id,
                        symbol=trade.symbol,
                        quantity=trade.quantity,
                        average_cost=trade.price,
                        current_price=trade.price,
                        total_cost=trade.price * trade.quantity,
                        market_value=trade.price * trade.quantity,
                        position_type="long"
                    )
                    self.db.add(holding)
                
                # Update portfolio cash (deduct purchase amount)
                portfolio.current_cash -= trade.net_amount
                
            else:  # sell
                if holding and holding.quantity >= trade.quantity:
                    # Calculate realized P&L
                    realized_pnl = (trade.price - holding.average_cost) * trade.quantity
                    trade.realized_pnl = realized_pnl
                    trade.realized_pnl_percent = (realized_pnl / (holding.average_cost * trade.quantity)) * 100
                    
                    # Update holding
                    holding.quantity -= trade.quantity
                    holding.total_cost = holding.average_cost * holding.quantity
                    holding.market_value = holding.current_price * holding.quantity
                    
                    if holding.quantity == 0:
                        holding.is_active = False
                    
                    holding.updated_at = datetime.utcnow()
                    
                    # Update portfolio cash (add sale proceeds)
                    portfolio.current_cash += trade.total_amount - trade.commission - trade.fees
                    portfolio.realized_pnl += realized_pnl
                
            # Recalculate unrealized P&L for the holding
            if holding and holding.is_active:
                holding.unrealized_pnl = holding.market_value - holding.total_cost
                if holding.total_cost > 0:
                    holding.unrealized_pnl_percent = (holding.unrealized_pnl / holding.total_cost) * 100
                
            portfolio.updated_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Failed to update portfolio for trade: {e}")
            raise
    
    async def get_user_trades(self, user_id: UUID, portfolio_id: Optional[UUID] = None,
                              symbol: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Trade]:
        """Get user trades with optional filters"""
        try:
            stmt = select(Trade).where(Trade.user_id == user_id)
            
            if portfolio_id:
                stmt = stmt.where(Trade.portfolio_id == portfolio_id)
            
            if symbol:
                stmt = stmt.where(Trade.symbol == symbol)
            
            stmt = stmt.order_by(Trade.executed_at.desc()).limit(limit).offset(offset)
            
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Failed to get trades for user {user_id}: {e}")
            return []
    
    async def get_trading_statistics(self, user_id: UUID, portfolio_id: Optional[UUID] = None,
                                     period_days: int = 30) -> Dict[str, Any]:
        """Calculate trading statistics"""
        try:
            # Date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=period_days)
            
            # Base query
            stmt = select(Trade).where(
                and_(
                    Trade.user_id == user_id,
                    Trade.executed_at >= start_date,
                    Trade.executed_at <= end_date
                )
            )
            
            if portfolio_id:
                stmt = stmt.where(Trade.portfolio_id == portfolio_id)
            
            result = await self.db.execute(stmt)
            trades = result.scalars().all()
            
            # Calculate statistics
            stats = {
                "period_days": period_days,
                "total_trades": len(trades),
                "buy_trades": len([t for t in trades if t.side == "buy"]),
                "sell_trades": len([t for t in trades if t.side == "sell"]),
                "total_volume": sum(float(t.total_amount) for t in trades),
                "total_commission": sum(float(t.commission) for t in trades),
                "total_fees": sum(float(t.fees) for t in trades),
                "realized_pnl": sum(float(t.realized_pnl or 0) for t in trades),
                "winning_trades": len([t for t in trades if t.realized_pnl and t.realized_pnl > 0]),
                "losing_trades": len([t for t in trades if t.realized_pnl and t.realized_pnl < 0]),
                "win_rate": 0,
                "average_trade_size": 0,
                "largest_win": 0,
                "largest_loss": 0,
                "symbols_traded": list(set(t.symbol for t in trades))
            }
            
            if stats["total_trades"] > 0:
                stats["average_trade_size"] = stats["total_volume"] / stats["total_trades"]
                
                realized_pnls = [float(t.realized_pnl or 0) for t in trades if t.realized_pnl is not None]
                if realized_pnls:
                    stats["win_rate"] = (stats["winning_trades"] / len(realized_pnls)) * 100
                    stats["largest_win"] = max(realized_pnls) if realized_pnls else 0
                    stats["largest_loss"] = min(realized_pnls) if realized_pnls else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to calculate trading statistics: {e}")
            return {}