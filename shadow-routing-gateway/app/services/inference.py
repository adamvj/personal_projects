"""Mock Champion and Shadow model endpoints.

A standalone FastAPI app (run separately from the gateway) that simulates two
model versions behind HTTP endpoints:

* **Champion** — the stable production model: fast, reliable.
* **Shadow**   — the candidate model: slightly different weights (prediction
  drift), higher and more variable latency, and an injectable failure rate so
  the gateway's error isolation can be exercised.

Run locally::

    uvicorn app.services.inference:app --port 9000

Tunables (environment variables):

* ``MOCK_SHADOW_FAILURE_RATE``  — probability of a 500 from the shadow (default 0.05)
* ``MOCK_SHADOW_DRIFT``         — weight perturbation magnitude (default 0.15)
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import os
import random
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, model_validator

SHADOW_FAILURE_RATE = float(os.getenv("MOCK_SHADOW_FAILURE_RATE", "0.05"))
SHADOW_DRIFT = float(os.getenv("MOCK_SHADOW_DRIFT", "0.15"))

FEATURE_DIM = 8
OUTPUT_DIM = 3

# Deterministic weight matrices so predictions are reproducible across runs.
_rng = random.Random(42)
_CHAMPION_WEIGHTS = [
    [_rng.uniform(-1, 1) for _ in range(FEATURE_DIM)] for _ in range(OUTPUT_DIM)
]
_drift_rng = random.Random(7)
_SHADOW_WEIGHTS = [
    [w + _drift_rng.uniform(-SHADOW_DRIFT, SHADOW_DRIFT) for w in row]
    for row in _CHAMPION_WEIGHTS
]


class InferenceRequest(BaseModel):
    """Numerical features or raw text — at least one must be provided."""

    features: list[float] | None = None
    text: str | None = None

    @model_validator(mode="after")
    def _require_input(self) -> "InferenceRequest":
        if self.features is None and self.text is None:
            raise ValueError("Provide either 'features' or 'text'")
        return self


def _vectorize(request: InferenceRequest) -> list[float]:
    """Project the input into a fixed-size feature vector."""
    if request.features is not None:
        vec = list(request.features)[:FEATURE_DIM]
        vec += [0.0] * (FEATURE_DIM - len(vec))
        return vec
    # Deterministic hash-based embedding for text input.
    digest = hashlib.sha256(request.text.encode("utf-8")).digest()
    return [(digest[i] / 127.5) - 1.0 for i in range(FEATURE_DIM)]


def _forward(vector: list[float], weights: list[list[float]]) -> list[float]:
    """Single linear layer + sigmoid, producing an OUTPUT_DIM prediction."""
    return [
        1.0 / (1.0 + math.exp(-sum(w * x for w, x in zip(row, vector))))
        for row in weights
    ]


async def _simulate_latency(low_ms: float, high_ms: float) -> float:
    delay = random.uniform(low_ms, high_ms) / 1000.0
    await asyncio.sleep(delay)
    return delay * 1000.0


app = FastAPI(
    title="Mock Model Endpoints",
    description="Simulated Champion and Shadow model services.",
    version="1.0.0",
)


@app.post("/champion/predict")
async def champion_predict(request: InferenceRequest) -> dict:
    """Stable production model: 20–80 ms latency, always available."""
    start = time.perf_counter()
    await _simulate_latency(20, 80)
    prediction = _forward(_vectorize(request), _CHAMPION_WEIGHTS)
    return {
        "model_name": "champion",
        "model_version": "v1.4.2",
        "prediction": prediction,
        "inference_time_ms": round((time.perf_counter() - start) * 1000, 3),
    }


@app.post("/shadow/predict")
async def shadow_predict(request: InferenceRequest) -> dict:
    """Candidate model: 40–250 ms latency, occasional injected failures."""
    if random.random() < SHADOW_FAILURE_RATE:
        raise HTTPException(status_code=500, detail="Injected shadow model failure")
    start = time.perf_counter()
    await _simulate_latency(40, 250)
    prediction = _forward(_vectorize(request), _SHADOW_WEIGHTS)
    return {
        "model_name": "shadow",
        "model_version": "v2.0.0-rc1",
        "prediction": prediction,
        "inference_time_ms": round((time.perf_counter() - start) * 1000, 3),
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "shadow_failure_rate": SHADOW_FAILURE_RATE}
