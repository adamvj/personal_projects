# syntax=docker/dockerfile:1

# =============================================================================
# Stage 1 — builder: resolve and install dependencies into an isolated venv
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2 — runtime: minimal image, non-root user, venv copied from builder
# =============================================================================
FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN useradd --create-home --shell /usr/sbin/nologin appuser

WORKDIR /srv

COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY dashboard.py .

RUN mkdir -p /srv/data && chown -R appuser:appuser /srv

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
