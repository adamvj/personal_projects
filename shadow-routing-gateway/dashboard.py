"""Streamlit observability dashboard for the Shadow-Routing Gateway.

Reads comparison telemetry from the SQLite database written by the gateway's
background tasks and renders near-real-time charts for latency overhead and
prediction drift.

Run locally::

    streamlit run dashboard.py
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("GATEWAY_DATABASE_URL", "sqlite:///./data/shadow_metrics.db")

st.set_page_config(
    page_title="Shadow-Routing Gateway",
    page_icon="🔀",
    layout="wide",
)


@st.cache_resource
def get_engine():
    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    return create_engine(DATABASE_URL, connect_args=connect_args)


@st.cache_data(ttl=5)
def load_data(limit: int) -> pd.DataFrame:
    query = f"""
        SELECT request_id, timestamp, champion_latency_ms, shadow_latency_ms,
               latency_delta_ms, mse, cosine_similarity, drift_score, shadow_status
        FROM comparison_metrics
        ORDER BY timestamp DESC
        LIMIT {int(limit)}
    """
    try:
        df = pd.read_sql(query, get_engine())
    except Exception:
        return pd.DataFrame()
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


# --- sidebar -----------------------------------------------------------------
st.sidebar.title("🔀 Shadow Gateway")
st.sidebar.caption("Champion vs. Shadow observability")
lookback = st.sidebar.select_slider(
    "Requests to display", options=[100, 250, 500, 1000, 5000], value=500
)
drift_threshold = st.sidebar.slider("Drift alert threshold", 0.0, 1.0, 0.10, 0.01)
if st.sidebar.button("Refresh now", use_container_width=True):
    load_data.clear()

df = load_data(lookback)

st.title("Asynchronous Shadow-Routing Inference Gateway")

if df.empty:
    st.info(
        "No telemetry yet. Send traffic to the gateway:\n\n"
        "```bash\ncurl -X POST http://localhost:8000/predict "
        '-H "Content-Type: application/json" '
        '-d \'{"features": [0.5, 1.2, -0.3, 0.8]}\'\n```'
    )
    st.stop()

ok = df[df["shadow_status"] == "success"]

# --- KPI row -------------------------------------------------------------------
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Comparisons", f"{len(df):,}")
k2.metric("Champion p50 latency", f"{df['champion_latency_ms'].median():.0f} ms")
k3.metric(
    "Shadow p50 latency",
    f"{ok['shadow_latency_ms'].median():.0f} ms" if not ok.empty else "—",
)
k4.metric(
    "Mean drift score",
    f"{ok['drift_score'].mean():.4f}" if not ok.empty else "—",
    delta=(
        f"{ok['drift_score'].mean() - drift_threshold:+.4f} vs threshold"
        if not ok.empty
        else None
    ),
    delta_color="inverse",
)
k5.metric(
    "Shadow error rate",
    f"{(1 - len(ok) / len(df)) * 100:.1f} %",
)

if not ok.empty and ok["drift_score"].mean() > drift_threshold:
    st.warning(
        f"Mean drift score ({ok['drift_score'].mean():.4f}) exceeds the "
        f"alert threshold ({drift_threshold:.2f}). The Shadow model is "
        "diverging from the Champion."
    )

st.divider()

# --- latency ---------------------------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("Latency: Champion vs. Shadow")
    st.caption("Client-facing latency is the Champion line only — shadow calls run off the request path.")
    latency_df = df.set_index("timestamp")[["champion_latency_ms", "shadow_latency_ms"]]
    latency_df.columns = ["Champion (ms)", "Shadow (ms)"]
    st.line_chart(latency_df, height=300)

with right:
    st.subheader("Shadow latency overhead (Δ ms)")
    st.caption("shadow_latency − champion_latency per request. Absorbed asynchronously, never client-visible.")
    delta_df = ok.set_index("timestamp")[["latency_delta_ms"]]
    delta_df.columns = ["Δ latency (ms)"]
    st.area_chart(delta_df, height=300)

# --- drift -------------------------------------------------------------------------
left2, right2 = st.columns(2)

with left2:
    st.subheader("Prediction drift over time")
    st.caption("Composite score blending bounded MSE and cosine divergence (0 = identical outputs).")
    drift_df = ok.set_index("timestamp")[["drift_score"]]
    drift_df.columns = ["Drift score"]
    st.line_chart(drift_df, height=300)

with right2:
    st.subheader("Divergence metrics")
    st.caption("Raw MSE and cosine similarity between prediction vectors.")
    div_df = ok.set_index("timestamp")[["mse", "cosine_similarity"]]
    div_df.columns = ["MSE", "Cosine similarity"]
    st.line_chart(div_df, height=300)

# --- status + recent records ---------------------------------------------------------
st.subheader("Shadow request outcomes")
status_counts = df["shadow_status"].value_counts().rename_axis("status").reset_index(name="count")
st.bar_chart(status_counts.set_index("status"), height=200)

st.subheader("Most recent comparisons")
st.dataframe(
    df.sort_values("timestamp", ascending=False).head(25),
    use_container_width=True,
    hide_index=True,
)
