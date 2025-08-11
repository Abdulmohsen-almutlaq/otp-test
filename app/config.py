import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/otpdb")
    
    # Redis (for rate limiting and caching)
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Security
    master_secret: str = os.getenv("MASTER_SECRET", "")
    api_key: str = os.getenv("API_KEY", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    
    # OTP Configuration
    otp_digits: int = int(os.getenv("OTP_DIGITS", "6"))
    otp_interval: int = int(os.getenv("OTP_INTERVAL", "30"))
    otp_window: int = int(os.getenv("OTP_WINDOW", "1"))
    
    # Rate Limiting
    rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
    rate_limit_window: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    # Application
    app_name: str = "OTP Service"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    environment: str = os.getenv("ENVIRONMENT", "production")
    
    # Render specific
    port: int = int(os.getenv("PORT", "8000"))
    
    class Config:
        env_file = ".env"

settings = Settings()
