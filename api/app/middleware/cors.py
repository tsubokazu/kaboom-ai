from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings

def setup_cors(app: FastAPI) -> None:
    """Setup CORS middleware with CloudRun support"""
    
    # Dynamic origins for CloudRun
    allowed_origins = settings.ALLOWED_ORIGINS.copy()
    
    # Add CloudRun service URL if available
    if settings.is_cloud_run and settings.CLOUD_RUN_SERVICE:
        cloud_run_url = f"https://{settings.CLOUD_RUN_SERVICE}-{settings.GOOGLE_CLOUD_PROJECT}.a.run.app"
        allowed_origins.append(cloud_run_url)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"]
    )