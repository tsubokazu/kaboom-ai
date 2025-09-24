import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8080"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Cloud Run optimization flags
    DISABLE_REDIS: bool = os.getenv("DISABLE_REDIS", "False").lower() == "true"
    DISABLE_WEBSOCKET: bool = os.getenv("DISABLE_WEBSOCKET", "False").lower() == "true"
    DISABLE_REALTIME: bool = os.getenv("DISABLE_REALTIME", "False").lower() == "true"
    DISABLE_DATABASE: bool = os.getenv("DISABLE_DATABASE", "False").lower() == "true"
    
    # CORS Configuration
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:3001",
        "https://*.vercel.app",   # Vercel deployments
        "https://*.run.app"       # CloudRun deployments
    ]
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # Database Configuration (PostgreSQL via Supabase)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DB_ECHO: bool = os.getenv("DB_ECHO", "False").lower() == "true"
    
    # Redis Configuration for WebSocket scaling
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # External APIs - OpenRouter Integration
    OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_DEBUG: bool = os.getenv("OPENROUTER_DEBUG", "False").lower() == "true"
    OPENROUTER_LOG_REQUESTS: bool = os.getenv("OPENROUTER_LOG_REQUESTS", "True").lower() == "true"
    OPENROUTER_COST_TRACKING: bool = os.getenv("OPENROUTER_COST_TRACKING", "True").lower() == "true"
    
    # Legacy API Keys (for fallback if needed)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # Trading APIs
    TACHIBANA_API_KEY: Optional[str] = os.getenv("TACHIBANA_API_KEY")
    TACHIBANA_API_SECRET: Optional[str] = os.getenv("TACHIBANA_API_SECRET")
    
    # WebSocket Configuration
    WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))
    WS_MAX_CONNECTIONS: int = int(os.getenv("WS_MAX_CONNECTIONS", "1000"))
    
    # Background Tasks
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

    # Cloud Tasks Configuration
    USE_CLOUD_TASKS: bool = os.getenv("USE_CLOUD_TASKS", "false").lower() == "true"
    CLOUD_TASKS_LOCATION: str = os.getenv("CLOUD_TASKS_LOCATION", "asia-northeast1")
    CLOUD_RUN_SERVICE_URL: str = os.getenv("CLOUD_RUN_SERVICE_URL", "http://localhost:8080")
    
    # Market Data Configuration
    MARKET_DATA_UPDATE_INTERVAL: int = int(os.getenv("MARKET_DATA_UPDATE_INTERVAL", "5"))  # seconds
    SYSTEM_METRICS_UPDATE_INTERVAL: int = int(os.getenv("SYSTEM_METRICS_UPDATE_INTERVAL", "30"))  # seconds
    
    # CloudRun Configuration
    GOOGLE_CLOUD_PROJECT: Optional[str] = os.getenv("GOOGLE_CLOUD_PROJECT")
    CLOUD_RUN_SERVICE: Optional[str] = os.getenv("CLOUD_RUN_SERVICE")
    
    # Security
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))

    # Ingest API token (for n8n scheduling etc.)
    INGEST_API_TOKEN: Optional[str] = os.getenv("INGEST_API_TOKEN")
    
    # AI Configuration
    MAX_CONCURRENT_AI_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_AI_REQUESTS", "3"))
    AI_ANALYSIS_TIMEOUT: int = int(os.getenv("AI_ANALYSIS_TIMEOUT", "180"))  # 3 minutes
    OPENROUTER_CONCURRENT_REQUESTS: int = int(os.getenv("OPENROUTER_CONCURRENT_REQUESTS", "10"))
    
    # Application URL for OpenRouter headers
    APP_URL: str = os.getenv("APP_URL", "https://kaboom-trading.com")
    
    @property
    def is_cloud_run(self) -> bool:
        """Check if running on CloudRun"""
        return self.GOOGLE_CLOUD_PROJECT is not None and self.CLOUD_RUN_SERVICE is not None

# Global settings instance
settings = Settings()
