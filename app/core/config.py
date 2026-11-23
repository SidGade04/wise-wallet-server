# app/core/config.py
from __future__ import annotations
from typing import Literal, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Budget AI Backend"
    ENV: Literal["dev", "staging", "prod"] = os.getenv("ENV", "dev")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:8080")

    # Database (Supabase/Postgres via SQLAlchemy async)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")  # e.g. postgresql+asyncpg://user:pass@host:5432/db

    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-4-hydrogen")

    # Plaid (optional during local dev)
    PLAID_CLIENT_ID: Optional[str] = os.getenv("PLAID_CLIENT_ID")
    PLAID_SECRET: Optional[str] = os.getenv("PLAID_SECRET")
    PLAID_ENV: Literal["sandbox", "development", "production"] = os.getenv("PLAID_ENV", "sandbox")

    # Stripe (only required if you actually use billing right now)
    STRIPE_SECRET_KEY: Optional[str] = os.getenv("STRIPE_SECRET_KEY")
    REQUIRE_STRIPE: bool = os.getenv("REQUIRE_STRIPE", "false").lower() in {"1","true","yes"}

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local", ".env.server"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def _require_db_in_non_dev(cls, v: str, info):
        env = os.getenv("ENV", "dev")
        if env in {"staging", "prod"} and not v:
            raise ValueError("DATABASE_URL must be set for staging/prod.")
        return v

    @field_validator("STRIPE_SECRET_KEY")
    @classmethod
    def _conditionally_require_stripe(cls, v: Optional[str]):
        # Only enforce if you opted in (REQUIRE_STRIPE=true) or you’re in prod AND you actually use Stripe
        env = os.getenv("ENV", "dev")
        require_stripe = os.getenv("REQUIRE_STRIPE", "false").lower() in {"1","true","yes"}
        if require_stripe and not v:
            raise ValueError("STRIPE_SECRET_KEY is required when REQUIRE_STRIPE=true.")
        if env == "prod" and require_stripe and not v:
            raise ValueError("STRIPE_SECRET_KEY must be set in prod when Stripe is enabled.")
        return v

    def resolve_frontend_url(self, origin: Optional[str] = None) -> str:
        allowed = {
            self.FRONTEND_URL.rstrip("/"),
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "https://lemon-grass-096d3860f.6.azurestaticapps.net",
        }
        allowed.update(
            o.strip().rstrip("/")
            for o in os.getenv("CORS_ORIGINS", "").split(",")
            if o.strip()
        )
        if origin:
            origin = origin.rstrip("/")
            if origin in allowed:
                return origin
        return self.FRONTEND_URL.rstrip("/")

settings = Settings()
