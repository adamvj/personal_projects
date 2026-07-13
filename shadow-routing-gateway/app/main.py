"""Asynchronous Shadow-Routing Inference Gateway.

The gateway sits in front of a live **Champion** model. Every request is
served by the Champion on the critical path; a copy of the payload is then
mirrored to a candidate **Shadow** model via FastAPI ``BackgroundTasks`` —
after the response has already been returned to the client — so shadow
evaluation adds zero client-perceived latency.

Run locally::

    uvicorn app.main:app --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import sys
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from app import __version__
from app.config import Settings, get_settings
from app.db import init_db, record_comparison
from app.services import evaluator

logger = logging.getLogger("gateway")

# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------

_CONTEXT_FIELDS = (
    "event",
    "request_id",
    "model",
    "champion_latency_ms",
    "shadow_latency_ms",
    "latency_delta_ms",
    "drift_score",
    "mse",
    "cosine_similarity",
    "shadow_status",
    "status_code",
)


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON object (machine-parseable)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _CONTEXT_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class PredictionRequest(BaseModel):
    """Numerical features or raw text — at least one must be provided."""

    features: list[float] | None = Field(
        default=None, description="Numerical feature vector.", examples=[[0.5, 1.2, -0.3]]
    )
    text: str | None = Field(
        default=None, description="Raw text input.", examples=["a customer review"]
    )

    @model_validator(mode="after")
    def _require_input(self) -> "PredictionRequest":
        if self.features is None and self.text is None:
            raise ValueError("Provide either 'features' or 'text'")
        return self


class PredictionResponse(BaseModel):
    request_id: str
    model_name: str
    model_version: str
    prediction: list[float]
    latency_ms: float


# ---------------------------------------------------------------------------
# Shadow comparison background task
# ---------------------------------------------------------------------------


async def run_shadow_comparison(
    client: httpx.AsyncClient,
    settings: Settings,
    request_id: str,
    payload: dict,
    champion_output: dict,
    champion_latency_ms: float,
) -> None:
    """Mirror the payload to the Shadow model, evaluate divergence, persist.

    Executed by FastAPI's BackgroundTasks *after* the client response has
    been sent. Every failure mode is contained here — nothing can propagate
    back to the request path.
    """
    logger.info(
        "Shadow routing started",
        extra={"event": "shadow.dispatch", "request_id": request_id},
    )

    shadow_output: dict | None = None
    shadow_latency_ms: float | None = None
    shadow_status = "success"

    # --- call the shadow model with high-precision timing -----------------
    start = time.perf_counter()
    try:
        response = await client.post(
            settings.shadow_url,
            json=payload,
            timeout=settings.shadow_timeout_seconds,
        )
        shadow_latency_ms = (time.perf_counter() - start) * 1000.0
        response.raise_for_status()
        shadow_output = response.json()
    except httpx.TimeoutException:
        shadow_latency_ms = (time.perf_counter() - start) * 1000.0
        shadow_status = "timeout"
        logger.warning(
            "Shadow model timed out",
            extra={
                "event": "shadow.timeout",
                "request_id": request_id,
                "shadow_latency_ms": round(shadow_latency_ms, 3),
            },
        )
    except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
        shadow_latency_ms = (time.perf_counter() - start) * 1000.0
        shadow_status = "error"
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        logger.warning(
            "Shadow model request failed",
            extra={
                "event": "shadow.error",
                "request_id": request_id,
                "status_code": status_code,
                "shadow_latency_ms": round(shadow_latency_ms, 3),
            },
        )

    # --- evaluate divergence ----------------------------------------------
    mse = cos_sim = drift = latency_delta = None
    if shadow_status == "success" and shadow_output is not None:
        try:
            result = evaluator.evaluate(
                champion_prediction=champion_output["prediction"],
                shadow_prediction=shadow_output["prediction"],
                champion_latency_ms=champion_latency_ms,
                shadow_latency_ms=shadow_latency_ms,
            )
            mse = result.mse
            cos_sim = result.cosine_similarity
            drift = result.drift_score
            latency_delta = result.latency_delta_ms
            logger.info(
                "Shadow comparison completed",
                extra={
                    "event": "shadow.evaluated",
                    "request_id": request_id,
                    "champion_latency_ms": round(champion_latency_ms, 3),
                    "shadow_latency_ms": round(shadow_latency_ms, 3),
                    "latency_delta_ms": round(latency_delta, 3),
                    "mse": round(mse, 6),
                    "cosine_similarity": round(cos_sim, 6),
                    "drift_score": round(drift, 6),
                },
            )
        except (KeyError, ValueError, TypeError):
            shadow_status = "evaluation_failed"
            logger.exception(
                "Shadow output evaluation failed",
                extra={"event": "shadow.evaluation_failed", "request_id": request_id},
            )

    # --- persist telemetry (off the event loop) -----------------------------
    try:
        await asyncio.to_thread(
            record_comparison,
            request_id=request_id,
            champion_latency_ms=round(champion_latency_ms, 3),
            shadow_latency_ms=round(shadow_latency_ms, 3) if shadow_latency_ms else None,
            latency_delta_ms=round(latency_delta, 3) if latency_delta is not None else None,
            champion_output=json.dumps(champion_output),
            shadow_output=json.dumps(shadow_output) if shadow_output else None,
            mse=mse,
            cosine_similarity=cos_sim,
            drift_score=drift,
            shadow_status=shadow_status,
        )
    except Exception:
        logger.exception(
            "Telemetry persistence failed",
            extra={"event": "shadow.persist_failed", "request_id": request_id},
        )


# ---------------------------------------------------------------------------
# Application factory / lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    await asyncio.to_thread(init_db)

    limits = httpx.Limits(
        max_connections=settings.max_connections,
        max_keepalive_connections=settings.max_keepalive_connections,
    )
    app.state.client = httpx.AsyncClient(limits=limits)
    logger.info(
        "Gateway started",
        extra={"event": "gateway.startup", "model": settings.champion_url},
    )
    try:
        yield
    finally:
        await app.state.client.aclose()
        logger.info("Gateway stopped", extra={"event": "gateway.shutdown"})


app = FastAPI(
    title="Asynchronous Shadow-Routing Inference Gateway",
    description=(
        "Serves predictions from the live Champion model while asynchronously "
        "mirroring traffic to a Shadow candidate for offline comparison."
    ),
    version=__version__,
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/predict", response_model=PredictionResponse)
async def predict(
    request: PredictionRequest, background_tasks: BackgroundTasks
) -> PredictionResponse:
    """Serve a Champion prediction; mirror the payload to the Shadow model.

    The Champion call is awaited on the critical path. The Shadow call is
    scheduled as a background task that runs *after* this response has been
    sent, so shadow evaluation never affects client latency — even if the
    Shadow model is slow, failing, or down entirely.
    """
    settings = get_settings()
    request_id = str(uuid.uuid4())
    payload = request.model_dump(exclude_none=True)

    # --- Champion call (critical path) -------------------------------------
    start = time.perf_counter()
    try:
        response = await app.state.client.post(
            settings.champion_url,
            json=payload,
            timeout=settings.champion_timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error(
            "Champion model request failed",
            extra={
                "event": "champion.error",
                "request_id": request_id,
                "status_code": getattr(getattr(exc, "response", None), "status_code", None),
            },
        )
        raise HTTPException(status_code=502, detail="Champion model unavailable") from exc

    champion_latency_ms = (time.perf_counter() - start) * 1000.0
    champion_output = response.json()

    logger.info(
        "Champion prediction served",
        extra={
            "event": "champion.served",
            "request_id": request_id,
            "champion_latency_ms": round(champion_latency_ms, 3),
        },
    )

    # --- Shadow mirror (fire-and-forget, post-response) ---------------------
    if settings.shadow_enabled and random.random() < settings.shadow_sample_rate:
        background_tasks.add_task(
            run_shadow_comparison,
            app.state.client,
            settings,
            request_id,
            dict(payload),
            champion_output,
            champion_latency_ms,
        )

    return PredictionResponse(
        request_id=request_id,
        model_name=champion_output.get("model_name", "champion"),
        model_version=champion_output.get("model_version", "unknown"),
        prediction=champion_output["prediction"],
        latency_ms=round(champion_latency_ms, 3),
    )


@app.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "shadow_enabled": settings.shadow_enabled,
        "shadow_sample_rate": settings.shadow_sample_rate,
    }
