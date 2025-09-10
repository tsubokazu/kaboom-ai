"""
Trading models for order management and trade execution tracking.
Handles order lifecycle, trade history, and execution details.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Numeric, Integer, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
import uuid

from app.database.connection import Base


class OrderType(str, Enum):
    """Order types supported by the trading system"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    """Order sides for buy/sell operations"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order status throughout lifecycle"""
    PENDING = "pending"           # Order created, not yet submitted
    SUBMITTED = "submitted"       # Order submitted to broker
    PARTIALLY_FILLED = "partially_filled"  # Order partially executed
    FILLED = "filled"             # Order completely executed
    CANCELLED = "cancelled"       # Order cancelled
    REJECTED = "rejected"         # Order rejected by broker
    EXPIRED = "expired"           # Order expired


class TradeStatus(str, Enum):
    """Trade execution status"""
    PENDING = "pending"           # Trade pending execution
    EXECUTED = "executed"         # Trade successfully executed
    SETTLED = "settled"           # Trade settled (T+2)
    FAILED = "failed"             # Trade execution failed


class Order(Base):
    """
    Order model for tracking trading orders.
    
    Handles order creation, submission, and lifecycle management
    for both paper trading and real broker integration.
    """
    __tablename__ = "orders"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False, index=True)
    
    # Order identification
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    external_order_id = Column(String(100), nullable=True, index=True)  # Broker order ID
    
    # Order details
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # buy, sell
    order_type = Column(String(20), nullable=False)  # market, limit, stop, stop_limit
    quantity = Column(Integer, nullable=False)
    
    # Price information
    limit_price = Column(Numeric(12, 2), nullable=True)
    stop_price = Column(Numeric(12, 2), nullable=True)
    average_fill_price = Column(Numeric(12, 2), nullable=True)
    
    # Execution tracking
    filled_quantity = Column(Integer, default=0)
    remaining_quantity = Column(Integer, nullable=False)
    status = Column(String(20), default="pending", index=True)
    
    # Financial calculations
    estimated_cost = Column(Numeric(15, 2), nullable=True)  # Estimated total cost
    actual_cost = Column(Numeric(15, 2), nullable=True)     # Actual execution cost
    commission = Column(Numeric(10, 2), default=Decimal('0'))
    fees = Column(Numeric(10, 2), default=Decimal('0'))
    
    # Order settings
    time_in_force = Column(String(10), default="DAY")  # DAY, GTC, IOC, FOK
    is_paper_trade = Column(Boolean, default=False)
    
    # AI and automation
    is_ai_generated = Column(Boolean, default=False)
    ai_strategy = Column(String(100), nullable=True)
    ai_confidence = Column(Numeric(5, 4), nullable=True)  # AI confidence 0-1
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    filled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional data
    notes = Column(Text, nullable=True)
    order_metadata = Column(JSON, default=dict)  # Additional order metadata
    
    # Relationships
    user = relationship("User", back_populates="orders")
    portfolio = relationship("Portfolio", back_populates="orders")
    trades = relationship("Trade", back_populates="order")
    
    def __repr__(self) -> str:
        return f"<Order(id={self.id}, symbol={self.symbol}, side={self.side}, quantity={self.quantity})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary representation"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "portfolio_id": str(self.portfolio_id),
            "order_number": self.order_number,
            "external_order_id": self.external_order_id,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "limit_price": float(self.limit_price) if self.limit_price else None,
            "stop_price": float(self.stop_price) if self.stop_price else None,
            "average_fill_price": float(self.average_fill_price) if self.average_fill_price else None,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "status": self.status,
            "estimated_cost": float(self.estimated_cost) if self.estimated_cost else None,
            "actual_cost": float(self.actual_cost) if self.actual_cost else None,
            "commission": float(self.commission),
            "fees": float(self.fees),
            "time_in_force": self.time_in_force,
            "is_paper_trade": self.is_paper_trade,
            "is_ai_generated": self.is_ai_generated,
            "ai_strategy": self.ai_strategy,
            "ai_confidence": float(self.ai_confidence) if self.ai_confidence else None,
            "notes": self.notes,
            "order_metadata": self.order_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class Trade(Base):
    """
    Trade model for tracking individual trade executions.
    
    Records actual trade executions, including partial fills
    and settlement details for portfolio tracking.
    """
    __tablename__ = "trades"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True, index=True)
    
    # Trade identification
    trade_number = Column(String(50), unique=True, nullable=False, index=True)
    external_trade_id = Column(String(100), nullable=True, index=True)  # Broker trade ID
    
    # Trade details
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # buy, sell
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    
    # Financial details
    total_amount = Column(Numeric(15, 2), nullable=False)  # quantity * price
    commission = Column(Numeric(10, 2), default=Decimal('0'))
    fees = Column(Numeric(10, 2), default=Decimal('0'))
    net_amount = Column(Numeric(15, 2), nullable=False)  # total_amount + commission + fees
    
    # Trade status
    status = Column(String(20), default="executed", index=True)
    is_paper_trade = Column(Boolean, default=False)
    
    # Settlement tracking
    trade_date = Column(DateTime(timezone=True), nullable=False)
    settlement_date = Column(DateTime(timezone=True), nullable=True)  # T+2 for stocks
    is_settled = Column(Boolean, default=False)
    
    # Performance tracking (for closed positions)
    realized_pnl = Column(Numeric(15, 2), nullable=True)
    realized_pnl_percent = Column(Numeric(8, 4), nullable=True)
    
    # Market data at execution
    market_price_at_execution = Column(Numeric(12, 2), nullable=True)
    bid_price = Column(Numeric(12, 2), nullable=True)
    ask_price = Column(Numeric(12, 2), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Additional data
    notes = Column(Text, nullable=True)
    trade_metadata = Column(JSON, default=dict)  # Additional trade metadata
    
    # Relationships
    user = relationship("User", back_populates="trades")
    portfolio = relationship("Portfolio", back_populates="trades")
    order = relationship("Order", back_populates="trades")
    
    def __repr__(self) -> str:
        return f"<Trade(id={self.id}, symbol={self.symbol}, side={self.side}, quantity={self.quantity}, price={self.price})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trade to dictionary representation"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "portfolio_id": str(self.portfolio_id),
            "order_id": str(self.order_id) if self.order_id else None,
            "trade_number": self.trade_number,
            "external_trade_id": self.external_trade_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": float(self.price),
            "total_amount": float(self.total_amount),
            "commission": float(self.commission),
            "fees": float(self.fees),
            "net_amount": float(self.net_amount),
            "status": self.status,
            "is_paper_trade": self.is_paper_trade,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "settlement_date": self.settlement_date.isoformat() if self.settlement_date else None,
            "is_settled": self.is_settled,
            "realized_pnl": float(self.realized_pnl) if self.realized_pnl else None,
            "realized_pnl_percent": float(self.realized_pnl_percent) if self.realized_pnl_percent else None,
            "market_price_at_execution": float(self.market_price_at_execution) if self.market_price_at_execution else None,
            "bid_price": float(self.bid_price) if self.bid_price else None,
            "ask_price": float(self.ask_price) if self.ask_price else None,
            "notes": self.notes,
            "trade_metadata": self.trade_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }