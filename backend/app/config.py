"""
Application configuration, loaded from environment variables / .env.

Foundation-phase note: only DATABASE_URL is actually consumed right
now (by app/database.py and alembic/env.py). JWT and Anthropic settings
are defined here so config doesn't need to be revisited when auth and
the Claude tool-use integration are built in later phases.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./financeos.db"
    anthropic_api_key: str = ""
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
