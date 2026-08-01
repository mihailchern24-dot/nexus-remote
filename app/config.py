from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./nexus.db"
    JWT_SECRET: str = "nexus-super-secret-jwt-key-2026-change-me-later-minimum-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = "noreply@nexus.local"
    class Config:
        env_file = ".env"
settings = Settings()
