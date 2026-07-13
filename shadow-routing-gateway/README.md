# Asynchronous Shadow-Routing Inference Gateway

A high-throughput traffic-splitting gateway for evaluating a candidate ("Shadow") machine learning model against the live production ("Champion") model — **with zero impact on client-side latency**.

Every inbound prediction request is served by the Champion on the critical path. After the response has been returned to the client, the gateway asynchronously mirrors an identical copy of the payload to the Shadow model, times both models with high-precision counters, computes output divergence (MSE, cosine similarity, composite drift score), and persists the full comparison record to SQLite. A Streamlit dashboard visualizes latency overhead and prediction drift in near real time.

## Why shadow routing?

Deploying a new model directly to production is risky: offline evaluation rarely captures real traffic distributions, latency behavior under load, or silent output regressions. Shadow routing (also called *dark launching* or *traffic mirroring*) answers the question **"how would the new model behave on real production traffic?"** without exposing a single user to it:

- Clients only ever receive Champion predictions — the Shadow's output is never returned.
- Shadow inference happens **after** the client response is flushed, so a slow, failing, or completely down Shadow adds **0 ms** to client latency.
- Every request produces a paired (Champion, Shadow) observation — the ideal dataset for a promotion decision.

## Architecture

```
                          ┌────────────────────────────────────────────┐
                          │            FastAPI Gateway :8000           │
                          │                                            │
 Client ── POST /predict ─▶  1. await Champion (critical path)         │
        ◀── response ─────│  2. flush response to client               │
                          │  3. BackgroundTask fires *after* response: │
                          │       • mirror payload → Shadow            │
                          │       • time.perf_counter() both models    │
                          │       • evaluator: MSE / cosine / drift    │
                          │       • commit telemetry → SQLite          │
                          └──────┬──────────────────────┬──────────────┘
                                 │                      │
                        ┌────────▼───────┐     ┌────────▼───────┐
                        │ Champion :9000 │     │  Shadow :9000  │
                        │ v1.4.2 (live)  │     │ v2.0.0-rc1     │
                        │ 20–80 ms       │     │ 40–250 ms, 5%  │
                        │                │     │ injected fails │
                        └────────────────┘     └────────────────┘

                                 SQLite (comparison_metrics)
                                          │
                                 ┌────────▼────────┐
                                 │ Streamlit :8501 │
                                 │   dashboard     │
                                 └─────────────────┘
```

### Request lifecycle

1. `POST /predict` is validated by Pydantic (numerical `features` or raw `text`).
2. The gateway awaits the Champion via a shared, connection-pooled `httpx.AsyncClient` and measures latency with `time.perf_counter()`.
3. The Champion prediction is returned to the client immediately.
4. FastAPI's `BackgroundTasks` framework — which executes **after the response is sent** — clones the payload and fires a non-blocking request to the Shadow model.
5. On Shadow completion the evaluator computes Mean Squared Error, cosine similarity, a composite drift score, and the latency delta; all telemetry is committed to SQLite via `asyncio.to_thread` so the blocking write never touches the event loop.
6. If the Shadow times out or errors, the failure is contained entirely within the background task: the outcome is logged and recorded (`shadow_status = timeout | error`), and the client is never affected.

## Project structure

```
shadow-routing-gateway/
├── app/
│   ├── main.py                 # FastAPI gateway: /predict, shadow BackgroundTask, JSON logging
│   ├── config.py               # pydantic-settings configuration (GATEWAY_* env vars)
│   ├── db.py                   # SQLAlchemy models + SQLite persistence
│   └── services/
│       ├── inference.py        # Mock Champion/Shadow endpoints (variable latency, injected failures)
│       └── evaluator.py        # MSE, cosine similarity, drift score, latency deltas
├── dashboard.py                # Streamlit observability dashboard
├── Dockerfile                  # Multi-stage build (builder venv → slim non-root runtime)
├── docker-compose.yml          # gateway + mock-models + dashboard, shared telemetry volume
├── requirements.txt
└── README.md
```

## Quickstart

### Option A — Docker Compose (recommended)

```bash
docker compose up --build
```

| Service      | URL                        |
| ------------ | -------------------------- |
| Gateway API  | http://localhost:8000/docs |
| Mock models  | http://localhost:9000/docs |
| Dashboard    | http://localhost:8501      |

### Option B — local Python

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Terminal 1 — mock Champion/Shadow endpoints
uvicorn app.services.inference:app --port 9000

# Terminal 2 — gateway
uvicorn app.main:app --port 8000

# Terminal 3 — dashboard
streamlit run dashboard.py
```

### Send traffic

```bash
# Numerical features
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [0.5, 1.2, -0.3, 0.8]}'

# Text input
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "the checkout flow feels much faster now"}'
```

Response (Champion only — the Shadow never touches the client path):

```json
{
  "request_id": "5b2f6c9e-...",
  "model_name": "champion",
  "model_version": "v1.4.2",
  "prediction": [0.7312, 0.2189, 0.5924],
  "latency_ms": 47.183
}
```

Generate sustained load to populate the dashboard:

```bash
for i in $(seq 1 200); do
  curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d "{\"features\": [0.$((RANDOM % 9)), 1.$((RANDOM % 9)), -0.$((RANDOM % 9))]}" > /dev/null &
done; wait
```

## Configuration

All settings are managed by `pydantic-settings` and overridable via environment variables (prefix `GATEWAY_`) or a `.env` file.

| Variable                           | Default                                     | Description                                      |
| ---------------------------------- | ------------------------------------------- | ------------------------------------------------ |
| `GATEWAY_CHAMPION_URL`             | `http://localhost:9000/champion/predict`    | Live production model endpoint                   |
| `GATEWAY_SHADOW_URL`               | `http://localhost:9000/shadow/predict`      | Candidate model endpoint                         |
| `GATEWAY_CHAMPION_TIMEOUT_SECONDS` | `5.0`                                       | Critical-path timeout                            |
| `GATEWAY_SHADOW_TIMEOUT_SECONDS`   | `10.0`                                      | Background shadow-call timeout                   |
| `GATEWAY_SHADOW_ENABLED`           | `true`                                      | Master switch for shadow mirroring               |
| `GATEWAY_SHADOW_SAMPLE_RATE`       | `1.0`                                       | Fraction of traffic mirrored (0.0–1.0)           |
| `GATEWAY_DATABASE_URL`             | `sqlite:///./data/shadow_metrics.db`        | SQLAlchemy database URL                          |
| `GATEWAY_LOG_LEVEL`                | `INFO`                                      | Structured-log level                             |
| `MOCK_SHADOW_FAILURE_RATE`         | `0.05`                                      | Mock service: probability of injected 500s       |
| `MOCK_SHADOW_DRIFT`                | `0.15`                                      | Mock service: weight perturbation magnitude      |

## Telemetry schema

Each shadow-routed request writes one row to `comparison_metrics`:

| Column                | Type     | Notes                                                    |
| --------------------- | -------- | -------------------------------------------------------- |
| `request_id`          | TEXT     | UUIDv4 correlating logs, response, and telemetry          |
| `timestamp`           | DATETIME | UTC, indexed                                              |
| `champion_latency_ms` | REAL     | `time.perf_counter()` around the Champion call            |
| `shadow_latency_ms`   | REAL     | `time.perf_counter()` around the Shadow call              |
| `latency_delta_ms`    | REAL     | `shadow − champion`                                       |
| `champion_output`     | TEXT     | Full Champion response (JSON)                             |
| `shadow_output`       | TEXT     | Full Shadow response (JSON), null on failure              |
| `mse`                 | REAL     | Mean Squared Error between prediction vectors             |
| `cosine_similarity`   | REAL     | Cosine similarity between prediction vectors              |
| `drift_score`         | REAL     | Composite divergence score in [0, 1]                      |
| `shadow_status`       | TEXT     | `success` \| `error` \| `timeout` \| `evaluation_failed`  |

**Drift score.** `0.5 · mse/(mse+1) + 0.5 · (1 − cos_sim)/2` — a bounded blend of magnitude divergence and angular divergence. `0` means identical outputs; values approaching `1` indicate severe disagreement.

## Structured logging

All gateway events are emitted as single-line JSON via Python's standard `logging` module, keyed by `request_id` for end-to-end traceability:

```json
{"ts": "2026-07-12T18:04:11+0000", "level": "INFO", "logger": "gateway", "message": "Shadow comparison completed", "event": "shadow.evaluated", "request_id": "5b2f6c9e-...", "champion_latency_ms": 47.183, "shadow_latency_ms": 212.905, "latency_delta_ms": 165.722, "mse": 0.001984, "cosine_similarity": 0.999871, "drift_score": 0.001055}
```

Key events: `gateway.startup`, `champion.served`, `champion.error`, `shadow.dispatch`, `shadow.evaluated`, `shadow.timeout`, `shadow.error`, `shadow.persist_failed`.

## Failure isolation guarantees

| Failure mode                     | Client impact | Recorded as              |
| -------------------------------- | ------------- | ------------------------ |
| Shadow returns 5xx               | None          | `shadow_status=error`    |
| Shadow exceeds timeout           | None          | `shadow_status=timeout`  |
| Shadow completely unreachable    | None          | `shadow_status=error`    |
| Shadow output malformed          | None          | `evaluation_failed`      |
| Telemetry DB write fails         | None          | Logged, dropped          |
| Champion fails                   | HTTP 502      | Not shadow-routed        |

The invariant: **nothing that happens after the Champion response is flushed can change what the client received.** Background tasks own their entire failure domain — every exception path is caught, logged, and recorded.

## Design decisions

- **`BackgroundTasks` over a message queue.** Starlette background tasks execute in-process after the response is sent — the simplest mechanism that satisfies the zero-latency-impact requirement. At larger scale the same task body drops cleanly onto Celery/ARQ/Kafka; the evaluation and persistence interfaces would not change.
- **Shared `httpx.AsyncClient`.** One connection-pooled client (created in the app lifespan) serves both Champion and Shadow calls, avoiding per-request TCP/TLS handshakes at high throughput.
- **SQLite + `asyncio.to_thread`.** A serverless file DB keeps the project dependency-free while a thread-dispatch keeps blocking commits off the event loop. Swapping `GATEWAY_DATABASE_URL` to Postgres requires no code changes.
- **Sampling knob.** `GATEWAY_SHADOW_SAMPLE_RATE` allows mirroring only a fraction of traffic — important when the Shadow's serving capacity is smaller than production's.
- **Multi-stage Docker build.** Dependencies compile in a builder stage; the runtime stage is a slim, non-root image containing only the venv and application code.

## Roadmap

- Replace in-process background tasks with a durable queue (ARQ/Celery) for at-least-once evaluation under process restarts.
- Champion/Shadow response caching keyed by payload hash to support idempotent replay.
- Statistical promotion gates (sequential testing on drift score) with automated alerting.
- Prometheus `/metrics` exporter alongside the SQLite sink.

## License

MIT
