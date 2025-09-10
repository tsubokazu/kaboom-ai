"""
Portfolio and Holding models for investment portfolio management.
Handles portfolio tracking, holdings, and performance calculations.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Numeric, Integer, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

from app.database.connection import Base


class Portfolio(Base):
    """
    Portfolio model for managing investment portfolios.
    
    Each user can have multiple portfolios for different strategies:
    - Main trading portfolio
    - Long-term investment portfolio  
    - Paper trading portfolio
    - AI strategy portfolios
    """
    __tablename__ = "portfolios"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Portfolio basic info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    portfolio_type = Column(String(50), default="trading")  # trading, investment, paper, ai_strategy
    
    # Financial data
    initial_capital = Column(Numeric(15, 2), nullable=False, default=Decimal('1000000'))  # 100万円
    current_cash = Column(Numeric(15, 2), nullable=False, default=Decimal('1000000'))
    total_value = Column(Numeric(15, 2), nullable=False, default=Decimal('1000000'))
    unrealized_pnl = Column(Numeric(15, 2), default=Decimal('0'))
    realized_pnl = Column(Numeric(15, 2), default=Decimal('0'))
    
    # Performance metrics
    total_return = Column(Numeric(8, 4), default=Decimal('0'))  # Total return percentage
    daily_return = Column(Numeric(8, 4), default=Decimal('0'))  # Daily return percentage
    max_drawdown = Column(Numeric(8, 4), default=Decimal('0'))  # Maximum drawdown percentage
    sharpe_ratio = Column(Numeric(6, 4), nullable=True)
    
    # Risk metrics
    var_95 = Column(Numeric(15, 2), nullable=True)  # Value at Risk (95% confidence)
    beta = Column(Numeric(6, 4), nullable=True)     # Beta vs market
    volatility = Column(Numeric(8, 4), nullable=True)  # Portfolio volatility
    
    # Portfolio settings
    is_active = Column(Boolean, default=True)
    is_paper_trading = Column(Boolean, default=False)
    currency = Column(String(3), default="JPY")
    
    # AI and strategy settings
    ai_enabled = Column(Boolean, default=False)
    rebalancing_frequency = Column(String(20), default="manual")  # manual, daily, weekly, monthly
    risk_limit = Column(Numeric(5, 2), default=Decimal('10'))  # Risk limit as percentage
    
    # JSON fields for flexible data
    strategy_settings = Column(JSON, default=dict)  # AI strategy parameters
    portfolio_metadata = Column(JSON, default=dict)          # Additional metadata
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_rebalanced_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    owner = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="portfolio")
    trades = relationship("Trade", back_populates="portfolio")
    
    def __repr__(self) -> str:
        return f"<Portfolio(id={self.id}, name={self.name}, user_id={self.user_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert portfolio to dictionary representation"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "description": self.description,
            "portfolio_type": self.portfolio_type,
            "initial_capital": float(self.initial_capital),
            "current_cash": float(self.current_cash),
            "total_value": float(self.total_value),
            "unrealized_pnl": float(self.unrealized_pnl),
            "realized_pnl": float(self.realized_pnl),
            "total_return": float(self.total_return),
            "daily_return": float(self.daily_return),
            "max_drawdown": float(self.max_drawdown),
            "sharpe_ratio": float(self.sharpe_ratio) if self.sharpe_ratio else None,
            "var_95": float(self.var_95) if self.var_95 else None,
            "beta": float(self.beta) if self.beta else None,
            "volatility": float(self.volatility) if self.volatility else None,
            "is_active": self.is_active,
            "is_paper_trading": self.is_paper_trading,
            "currency": self.currency,
            "ai_enabled": self.ai_enabled,
            "rebalancing_frequency": self.rebalancing_frequency,
            "risk_limit": float(self.risk_limit),
            "strategy_settings": self.strategy_settings or {},
            "portfolio_metadata": self.portfolio_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_rebalanced_at": self.last_rebalanced_at.isoformat() if self.last_rebalanced_at else None,
        }


class Holding(Base):
    """
    Holding model for individual stock positions within portfolios.
    
    Tracks current positions, average cost, unrealized P&L for each symbol.
    """
    __tablename__ = "holdings"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to portfolio
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False, index=True)
    
    # Stock information
    symbol = Column(String(20), nullable=False, index=True)  # e.g., "7203.T" for Toyota
    company_name = Column(String(255), nullable=True)
    sector = Column(String(100), nullable=True)
    market = Column(String(50), nullable=True)  # TSE, NASDAQ, NYSE, etc.
    
    # Position data
    quantity = Column(Integer, nullable=False, default=0)
    average_cost = Column(Numeric(12, 2), nullable=False, default=Decimal('0'))
    current_price = Column(Numeric(12, 2), nullable=False, default=Decimal('0'))
    market_value = Column(Numeric(15, 2), nullable=False, default=Decimal('0'))
    
    # P&L calculations
    unrealized_pnl = Column(Numeric(15, 2), default=Decimal('0'))
    unrealized_pnl_percent = Column(Numeric(8, 4), default=Decimal('0'))
    total_cost = Column(Numeric(15, 2), nullable=False, default=Decimal('0'))
    
    # Position metadata
    position_type = Column(String(10), default="long")  # long, short
    is_active = Column(Boolean, default=True)
    
    # Price tracking
    day_change = Column(Numeric(12, 2), default=Decimal('0'))
    day_change_percent = Column(Numeric(8, 4), default=Decimal('0'))
    week_high = Column(Numeric(12, 2), nullable=True)
    week_low = Column(Numeric(12, 2), nullable=True)
    
    # JSON fields
    holding_metadata = Column(JSON, default=dict)  # Additional stock-specific data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_price_update = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")
    
    def __repr__(self) -> str:
        return f"<Holding(symbol={self.symbol}, quantity={self.quantity}, portfolio_id={self.portfolio_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert holding to dictionary representation"""
        return {
            "id": str(self.id),
            "portfolio_id": str(self.portfolio_id),
            "symbol": self.symbol,
            "company_name": self.company_name,
            "sector": self.sector,
            "market": self.market,
            "quantity": self.quantity,
            "average_cost": float(self.average_cost),
            "current_price": float(self.current_price),
            "market_value": float(self.market_value),
            "unrealized_pnl": float(self.unrealized_pnl),
            "unrealized_pnl_percent": float(self.unrealized_pnl_percent),
            "total_cost": float(self.total_cost),
            "position_type": self.position_type,
            "is_active": self.is_active,
            "day_change": float(self.day_change),
            "day_change_percent": float(self.day_change_percent),
            "week_high": float(self.week_high) if self.week_high else None,
            "week_low": float(self.week_low) if self.week_low else None,
            "holding_metadata": self.holding_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_price_update": self.last_price_update.isoformat() if self.last_price_update else None,
        }
    
    def update_price(self, new_price: Decimal, day_change: Decimal = None) -> None:
        """Update current price and recalculate metrics"""
        self.current_price = new_price
        self.market_value = new_price * self.quantity
        
        if self.quantity > 0 and self.average_cost > 0:
            self.unrealized_pnl = self.market_value - self.total_cost
            self.unrealized_pnl_percent = (self.unrealized_pnl / self.total_cost) * 100
        
        if day_change is not None:
            self.day_change = day_change
            if self.current_price > 0:
                self.day_change_percent = (day_change / self.current_price) * 100
        
        self.last_price_update = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    @property
    def weight_in_portfolio(self) -> Decimal:
        """Calculate weight of this holding in the portfolio (requires portfolio total_value)"""
        if self.portfolio and self.portfolio.total_value > 0:
            return (self.market_value / self.portfolio.total_value) * 100
        return Decimal('0')