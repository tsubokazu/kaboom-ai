"""
Portfolio service for database operations.
Handles all portfolio and holdings related database interactions.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload
from uuid import UUID
import uuid
import logging

from app.models.user import User
from app.models.portfolio import Portfolio, Holding
from app.services.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class PortfolioService:
    """Service class for portfolio operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_portfolio(self, user_id: UUID, portfolio_data: Dict[str, Any]) -> Portfolio:
        """Create a new portfolio for user"""
        try:
            # Create portfolio with user_id
            portfolio = Portfolio(
                user_id=user_id,
                name=portfolio_data["name"],
                description=portfolio_data.get("description"),
                portfolio_type=portfolio_data.get("portfolio_type", "trading"),
                initial_capital=Decimal(str(portfolio_data.get("initial_capital", 1000000))),
                current_cash=Decimal(str(portfolio_data.get("initial_capital", 1000000))),
                total_value=Decimal(str(portfolio_data.get("initial_capital", 1000000))),
                currency=portfolio_data.get("currency", "JPY"),
                ai_enabled=portfolio_data.get("ai_enabled", False),
                rebalancing_frequency=portfolio_data.get("rebalancing_frequency", "manual"),
                risk_limit=Decimal(str(portfolio_data.get("risk_limit", 10))),
                strategy_settings=portfolio_data.get("strategy_settings", {}),
                portfolio_metadata=portfolio_data.get("metadata", {})
            )
            
            self.db.add(portfolio)
            await self.db.commit()
            await self.db.refresh(portfolio)
            
            # Cache portfolio data
            redis_client = await get_redis_client()
            await redis_client.set_cache(
                f"portfolio:{portfolio.id}",
                portfolio.to_dict(),
                expire_seconds=300
            )
            
            logger.info(f"Created portfolio {portfolio.id} for user {user_id}")
            return portfolio
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create portfolio for user {user_id}: {e}")
            raise
    
    async def get_portfolio(self, portfolio_id: UUID, user_id: UUID) -> Optional[Portfolio]:
        """Get portfolio by ID (with user ownership check)"""
        try:
            # Try cache first
            redis_client = await get_redis_client()
            cached_portfolio = await redis_client.get_cache(f"portfolio:{portfolio_id}")
            if cached_portfolio and cached_portfolio.get("user_id") == str(user_id):
                # Fetch fresh data for accuracy
                pass
            
            # Query database with holdings
            stmt = select(Portfolio).options(
                selectinload(Portfolio.holdings)
            ).where(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == user_id
            )
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            
            if portfolio:
                # Update cache
                await redis_client.set_cache(
                    f"portfolio:{portfolio_id}",
                    portfolio.to_dict(),
                    expire_seconds=300
                )
            
            return portfolio
            
        except Exception as e:
            logger.error(f"Failed to get portfolio {portfolio_id}: {e}")
            return None
    
    async def get_user_portfolios(self, user_id: UUID) -> List[Portfolio]:
        """Get all portfolios for a user"""
        try:
            stmt = select(Portfolio).options(
                selectinload(Portfolio.holdings)
            ).where(
                Portfolio.user_id == user_id,
                Portfolio.is_active == True
            ).order_by(Portfolio.created_at.desc())
            
            result = await self.db.execute(stmt)
            portfolios = result.scalars().all()
            
            return list(portfolios)
            
        except Exception as e:
            logger.error(f"Failed to get portfolios for user {user_id}: {e}")
            return []
    
    async def update_portfolio(self, portfolio_id: UUID, user_id: UUID, update_data: Dict[str, Any]) -> Optional[Portfolio]:
        """Update portfolio"""
        try:
            # Get portfolio
            portfolio = await self.get_portfolio(portfolio_id, user_id)
            if not portfolio:
                return None
            
            # Update fields
            for field, value in update_data.items():
                if hasattr(portfolio, field) and value is not None:
                    if field in ['initial_capital', 'current_cash', 'risk_limit']:
                        setattr(portfolio, field, Decimal(str(value)))
                    else:
                        setattr(portfolio, field, value)
            
            portfolio.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(portfolio)
            
            # Update cache
            redis_client = await get_redis_client()
            await redis_client.set_cache(
                f"portfolio:{portfolio_id}",
                portfolio.to_dict(),
                expire_seconds=300
            )
            
            logger.info(f"Updated portfolio {portfolio_id}")
            return portfolio
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update portfolio {portfolio_id}: {e}")
            raise
    
    async def delete_portfolio(self, portfolio_id: UUID, user_id: UUID) -> bool:
        """Delete portfolio (soft delete)"""
        try:
            portfolio = await self.get_portfolio(portfolio_id, user_id)
            if not portfolio:
                return False
            
            # Soft delete by setting is_active to False
            portfolio.is_active = False
            portfolio.updated_at = datetime.utcnow()
            
            await self.db.commit()
            
            # Remove from cache
            redis_client = await get_redis_client()
            await redis_client.delete_cache(f"portfolio:{portfolio_id}")
            
            logger.info(f"Deleted portfolio {portfolio_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete portfolio {portfolio_id}: {e}")
            return False
    
    async def add_holding(self, portfolio_id: UUID, user_id: UUID, holding_data: Dict[str, Any]) -> Optional[Holding]:
        """Add holding to portfolio"""
        try:
            # Verify portfolio ownership
            portfolio = await self.get_portfolio(portfolio_id, user_id)
            if not portfolio:
                return None
            
            # Check if holding already exists for this symbol
            stmt = select(Holding).where(
                Holding.portfolio_id == portfolio_id,
                Holding.symbol == holding_data["symbol"],
                Holding.is_active == True
            )
            result = await self.db.execute(stmt)
            existing_holding = result.scalar_one_or_none()
            
            if existing_holding:
                # Update existing holding (average cost calculation)
                old_quantity = existing_holding.quantity
                old_cost = existing_holding.average_cost
                new_quantity = holding_data["quantity"]
                new_cost = Decimal(str(holding_data["average_cost"]))
                
                total_quantity = old_quantity + new_quantity
                if total_quantity > 0:
                    # Weighted average cost
                    total_cost_value = (old_quantity * old_cost) + (new_quantity * new_cost)
                    existing_holding.average_cost = total_cost_value / total_quantity
                    existing_holding.quantity = total_quantity
                    existing_holding.total_cost = existing_holding.average_cost * total_quantity
                    existing_holding.updated_at = datetime.utcnow()
                
                await self.db.commit()
                await self.db.refresh(existing_holding)
                return existing_holding
            else:
                # Create new holding
                holding = Holding(
                    portfolio_id=portfolio_id,
                    symbol=holding_data["symbol"],
                    company_name=holding_data.get("company_name"),
                    sector=holding_data.get("sector"),
                    market=holding_data.get("market", "TSE"),
                    quantity=holding_data["quantity"],
                    average_cost=Decimal(str(holding_data["average_cost"])),
                    current_price=Decimal(str(holding_data.get("current_price", holding_data["average_cost"]))),
                    total_cost=Decimal(str(holding_data["quantity"])) * Decimal(str(holding_data["average_cost"])),
                    position_type=holding_data.get("position_type", "long"),
                    holding_metadata=holding_data.get("metadata", {})
                )
                
                # Calculate market value and P&L
                holding.market_value = holding.current_price * holding.quantity
                holding.unrealized_pnl = holding.market_value - holding.total_cost
                if holding.total_cost > 0:
                    holding.unrealized_pnl_percent = (holding.unrealized_pnl / holding.total_cost) * 100
                
                self.db.add(holding)
                await self.db.commit()
                await self.db.refresh(holding)
                
                logger.info(f"Added holding {holding.symbol} to portfolio {portfolio_id}")
                return holding
                
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to add holding to portfolio {portfolio_id}: {e}")
            raise
    
    async def update_holding_price(self, holding_id: UUID, new_price: Decimal, day_change: Optional[Decimal] = None) -> Optional[Holding]:
        """Update holding price and recalculate metrics"""
        try:
            stmt = select(Holding).where(Holding.id == holding_id)
            result = await self.db.execute(stmt)
            holding = result.scalar_one_or_none()
            
            if not holding:
                return None
            
            # Update price using the model method
            holding.update_price(new_price, day_change)
            
            await self.db.commit()
            await self.db.refresh(holding)
            
            return holding
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update holding price for {holding_id}: {e}")
            return None
    
    async def calculate_portfolio_metrics(self, portfolio_id: UUID) -> Dict[str, Any]:
        """Calculate portfolio performance metrics"""
        try:
            # Get portfolio with holdings
            stmt = select(Portfolio).options(
                selectinload(Portfolio.holdings)
            ).where(Portfolio.id == portfolio_id)
            
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            
            if not portfolio:
                return {}
            
            # Calculate totals
            total_market_value = Decimal('0')
            total_unrealized_pnl = Decimal('0')
            total_cost = Decimal('0')
            
            for holding in portfolio.holdings:
                if holding.is_active:
                    total_market_value += holding.market_value
                    total_unrealized_pnl += holding.unrealized_pnl
                    total_cost += holding.total_cost
            
            # Update portfolio values
            portfolio.total_value = portfolio.current_cash + total_market_value
            portfolio.unrealized_pnl = total_unrealized_pnl
            
            if portfolio.initial_capital > 0:
                portfolio.total_return = ((portfolio.total_value - portfolio.initial_capital) / portfolio.initial_capital) * 100
            
            await self.db.commit()
            
            metrics = {
                "total_value": float(portfolio.total_value),
                "total_market_value": float(total_market_value),
                "current_cash": float(portfolio.current_cash),
                "unrealized_pnl": float(total_unrealized_pnl),
                "realized_pnl": float(portfolio.realized_pnl),
                "total_return": float(portfolio.total_return),
                "total_cost": float(total_cost),
                "cash_percentage": float(portfolio.current_cash / portfolio.total_value * 100) if portfolio.total_value > 0 else 0
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate portfolio metrics for {portfolio_id}: {e}")
            return {}