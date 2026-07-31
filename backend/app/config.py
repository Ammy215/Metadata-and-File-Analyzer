from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import json


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./fileshield.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    
    # File Upload
    MAX_FILE_SIZE: int = 104857600  # 100 MB
    UPLOAD_DIR: str = "./uploads"
    
    # JWT/Security
    # No insecure default: must be set via .env. A hardcoded fallback here
    # would let anyone with source access forge valid tokens for any user.
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days
    
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = "NOT_CONFIGURED_OPTIONAL"
    GOOGLE_CLIENT_SECRET: Optional[str] = "NOT_CONFIGURED_OPTIONAL"
    
    # CORS - Parse JSON string from .env or use default list
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:5173","http://localhost:8000","http://127.0.0.1:3000","http://127.0.0.1:5173"]'
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS from JSON string to list."""
        if isinstance(self.CORS_ORIGINS, str):
            try:
                return json.loads(self.CORS_ORIGINS)
            except json.JSONDecodeError:
                # Fallback to default if parsing fails
                return [
                    "http://localhost:3000",
                    "http://localhost:5173",
                    "http://localhost:8000",
                    "http://127.0.0.1:3000",
                    "http://127.0.0.1:5173",
                ]
        return self.CORS_ORIGINS
    
    # Report generation
    WEASYPRINT_ENABLED: bool = True
    
    # YARA rules path
    YARA_RULES_DIR: str = "./yara_rules"
    
    # Admin
    SUPER_ADMIN_EMAIL: str = "admin@fileshield.com"
    # No insecure default: must be set via .env, so a real credential is
    # never silently baked into source.
    SUPER_ADMIN_PASSWORD: str

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
