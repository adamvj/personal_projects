"""Lightweight SQLite/SQLAlchemy persistence layer for comparison telemetry.

The gateway writes one row per shadow-routed request. Writes happen inside
background tasks (off the request path), so a synchronous SQLite engine is
sufficient; callers dispatch writes via ``asyncio.to_thread`` to keep the
event loop unblocked.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import get_settings

logger = logging.getLogger("gateway.db")


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class ComparisonMetric(Base):
    """One Champion-vs-Shadow comparison record."""

    __tablename__ = "comparison_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    champion_latency_ms: Mapped[float] = mapped_column(Float)
    shadow_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_delta_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    champion_output: Mapped[str] = mapped_column(Text)
    shadow_output: Mapped[str | None] = mapped_column(Text, nullable=True)

    mse: Mapped[float | None] = mapped_column(Float, nullable=True)
    cosine_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    drift_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # success | error | timeout | evaluation_failed
    shadow_status: Mapped[str] = mapped_column(String(32), default="success", index=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<ComparisonMetric request_id={self.request_id!r} "
            f"drift={self.drift_score} status={self.shadow_status!r}>"
        )


def _build_engine():
    settings = get_settings()
    url = settings.database_url
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        # Ensure the parent directory of a file-backed SQLite DB exists.
        db_path = url.split("///", maxsplit=1)[-1]
        if db_path and db_path != ":memory:":
            Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create tables if they do not exist. Idempotent."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialised", extra={"event": "db.initialised"})


def record_comparison(**fields) -> None:
    """Persist a single comparison record.

    Intended to be called from a worker thread (``asyncio.to_thread``) so the
    blocking commit never runs on the event loop.
    """
    session = SessionLocal()
    try:
        session.add(ComparisonMetric(**fields))
        session.commit()
    except Exception:
        session.rollback()
        logger.exception(
            "Failed to persist comparison metrics",
            extra={"event": "db.write_failed", "request_id": fields.get("request_id")},
        )
    finally:
        session.close()
