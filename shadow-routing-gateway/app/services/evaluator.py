"""Champion-vs-Shadow output analysis.

Computes divergence metrics between the two models' prediction vectors
(Mean Squared Error and Cosine Similarity), a composite drift score in
``[0, 1]``, and latency deltas. Pure-Python implementation — no NumPy
dependency required for small prediction vectors.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationResult:
    """Divergence and latency telemetry for a single request."""

    mse: float
    cosine_similarity: float
    drift_score: float
    latency_delta_ms: float
    latency_overhead_pct: float


def mean_squared_error(a: list[float], b: list[float]) -> float:
    """MSE between two equal-length prediction vectors."""
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} != {len(b)}")
    if not a:
        raise ValueError("Cannot compute MSE of empty vectors")
    return sum((x - y) ** 2 for x, y in zip(a, b)) / len(a)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length prediction vectors.

    Returns 1.0 when both vectors are zero (identical degenerate outputs)
    and 0.0 when exactly one is zero.
    """
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} != {len(b)}")
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 and norm_b == 0.0:
        return 1.0
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    # Clamp for floating-point safety.
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


def compute_drift_score(mse: float, cos_sim: float) -> float:
    """Composite drift score in [0, 1]; higher means more divergence.

    Blends a bounded MSE term (``mse / (mse + 1)``) with angular
    divergence (``(1 - cos_sim) / 2``) so that both magnitude and
    directional disagreement contribute.
    """
    magnitude_term = mse / (mse + 1.0)
    angular_term = (1.0 - cos_sim) / 2.0
    return 0.5 * magnitude_term + 0.5 * angular_term


def evaluate(
    champion_prediction: list[float],
    shadow_prediction: list[float],
    champion_latency_ms: float,
    shadow_latency_ms: float,
) -> EvaluationResult:
    """Compare two model outputs and their latencies."""
    mse = mean_squared_error(champion_prediction, shadow_prediction)
    cos_sim = cosine_similarity(champion_prediction, shadow_prediction)
    drift = compute_drift_score(mse, cos_sim)

    latency_delta_ms = shadow_latency_ms - champion_latency_ms
    overhead_pct = (
        (latency_delta_ms / champion_latency_ms) * 100.0
        if champion_latency_ms > 0
        else 0.0
    )

    return EvaluationResult(
        mse=mse,
        cosine_similarity=cos_sim,
        drift_score=drift,
        latency_delta_ms=latency_delta_ms,
        latency_overhead_pct=overhead_pct,
    )
