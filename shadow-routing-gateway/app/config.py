"""Centralised configuration management using pydantic-settings.

All values can be overridden via environment variables prefixed with
``GATEWAY_`` (e.g. ``GATEWAY_CHAMPION_URL``) or via a local ``.env`` file.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the shadow-routing gateway."""

    model_config = SettingsConfigDict(
        env_prefix="GATEWAY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- application ---------------------------------------------------
    app_name: str = "shadow-routing-gateway"
    environment: str = "development"
    log_level: str = "INFO"

    # --- upstream model endpoints --------------------------------------
    champion_url: str = "http://localhost:9000/champion/predict"
    shadow_url: str = "http://localhost:9000/shadow/predict"

    # --- timeouts (seconds) ---------------------------------------------
    champion_timeout_seconds: float = Field(default=5.0, gt=0)
    shadow_timeout_seconds: float = Field(default=10.0, gt=0)

    # --- shadow routing behaviour ---------------------------------------
    shadow_enabled: bool = True
    shadow_sample_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Fraction of live traffic mirrored to the shadow model.",
    )

    # --- connection pooling ----------------------------------------------
    max_connections: int = Field(default=100, gt=0)
    max_keepalive_connections: int = Field(default=20, gt=0)

    # --- persistence ------------------------------------------------------
    database_url: str = "sqlite:///./data/shadow_metrics.db"


@lru_cache
def get_settings() -> Settings:
    """Return a cached, process-wide Settings instance."""
    return Settings()
