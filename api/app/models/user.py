"""
User model for authentication and user management.
Integrates with Supabase Auth while storing additional user data.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

from app.database.connection import Base


class User(Base):
    """
    User model for storing user profile and preferences.
    
    This model complements Supabase Auth:
    - Supabase handles authentication, sessions, and basic user data
    - This model stores trading-specific preferences and metadata
    """
    __tablename__ = "users"

    # Primary key - matches Supabase auth.users.id
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Supabase integration
    supabase_user_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    
    # Profile information
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    
    # User preferences
    display_name = Column(String(100), nullable=True)
    timezone = Column(String(50), default="Asia/Tokyo")
    language = Column(String(10), default="ja")
    
    # Trading preferences
    default_currency = Column(String(3), default="JPY")
    risk_tolerance = Column(String(20), default="moderate")  # conservative, moderate, aggressive
    trading_experience = Column(String(20), default="beginner")  # beginner, intermediate, advanced
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    
    # JSON fields for flexible data storage
    preferences = Column(JSON, default=dict)  # UI preferences, notification settings, etc.
    user_metadata = Column(JSON, default=dict)     # Additional flexible metadata
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    portfolios = relationship("Portfolio", back_populates="owner", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, display_name={self.display_name})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary representation"""
        return {
            "id": str(self.id),
            "supabase_user_id": str(self.supabase_user_id),
            "email": self.email,
            "full_name": self.full_name,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "timezone": self.timezone,
            "language": self.language,
            "default_currency": self.default_currency,
            "risk_tolerance": self.risk_tolerance,
            "trading_experience": self.trading_experience,
            "is_active": self.is_active,
            "is_premium": self.is_premium,
            "is_verified": self.is_verified,
            "preferences": self.preferences or {},
            "user_metadata": self.user_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update user from dictionary data"""
        updatable_fields = [
            'full_name', 'display_name', 'avatar_url', 'timezone', 'language',
            'default_currency', 'risk_tolerance', 'trading_experience',
            'is_active', 'is_premium', 'is_verified', 'preferences', 'user_metadata'
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(self, field, data[field])
        
        self.updated_at = datetime.utcnow()
    
    @property
    def is_beginner(self) -> bool:
        """Check if user is a beginner trader"""
        return self.trading_experience == "beginner"
    
    @property
    def can_access_advanced_features(self) -> bool:
        """Check if user can access advanced features"""
        return self.is_premium and self.trading_experience in ["intermediate", "advanced"]