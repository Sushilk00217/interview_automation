import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Postgres
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/interview_db")

    # LLM for question generation (OpenAI or Azure OpenAI)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "")  # e.g. Azure: https://xxx.openai.azure.com/
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # or gpt-4, etc.

    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Email Settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "")
    
    # Developer Emails (Comma separated in .env)
    _DEVELOPER_EMAILS_STR: str = os.getenv("DEVELOPER_EMAILS", "")
    
    @property
    def DEVELOPER_EMAILS(self) -> list[str]:
        if not self._DEVELOPER_EMAILS_STR:
            return []
        return [email.strip() for email in self._DEVELOPER_EMAILS_STR.split(",") if email.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
