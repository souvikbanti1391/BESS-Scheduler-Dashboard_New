# ============================================================
#   IEX MCP Predictor — Fully Working Version With Path Fix
# ============================================================

# --- FIX: Force Streamlit to correctly load utils ----
import sys
import os
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve()
UTILS_DIR = CURRENT_DIR.parent.parent / "utils"
sys.path.append(str(UTILS_DIR))

# ------------------------------------------------------

import streamlit as st
import pandas as pd
import requests

from api_helpers import sanitize_df_for_json
from plot_helpers import (
    gradient_line_with_delta,
    heatmap_hour_by_date,
    daily_profile_comparison,
    mcp_histogram
)
from insight_helpers import compute_insights


# -----------------------------
#   PAGE TITLE
# -----------------------------
st.title("🔍 IEX MCP Predictor — Full Visual Analytics Suite")


# -----------------------------
#   LOAD GLOBAL UPLOADED DATA
# -----------------------------
df = st.session_state.get("uploaded_df")

if df is None:
    st.warning("⚠️ Please upload MCP data from the left sidebar before using this page.")
    st.stop()

df_display = df.copy()
df_display["timestamp"] = pd.to_datetime(df_display["timestamp"], errors="coerce")


# -----------------------------
#   SUMMARY INSIGHT PANEL
# -----------------------------
st.subheader("📊 Summary Insight Panel")

try:
    insights = compute_insights(df)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Highest MCP (Rs/kWh)",
                  f"{insights['highest'][0]:.3f}",
                  f"@ {insights['highest'][1]}")
        st.metric("Lowest MCP (Rs/kWh)",
                  f"{insights['lowest'][0]:.3f}",
                  f"@ {insights['lowest'][1]}")

    with col2:
        st.metric("Average MCP", f"{insights['avg']:.3f}")
        st.metric("Median MCP", f"{insights['median']:.3f}")
        st.metric("Volatility (Std Dev)", f"{insights['std']:.3f}")

    with col3:
        st.metric("Peak Hour", f"{insights['peak_hour']:02d}:00")
        st.metric("Cheapest Hour", f"{insights['cheapest_hour']:02d}:00")
        st.metric("Trend Direction", insights['trend'])

    st.info(f"🟠 Detected {insights['spikes']} price spikes (>15% hourly jump).")

except Exception as e:
    st.error(f"Insight panel error: {e}")


# -----------------------------
#   TABS FOR ANALYTICAL PLOTS
# -----------------------------
tabs = st.tabs(["📈 Trend", "🔥 Heatmap", "📊 Profiles & Distribution"])


# ============================================
#   TAB 1: TREND VIEW + FORECAST
# ============================================
with tabs[0]:
    st.subheader("📈 MCP Trend (Last 7 Days + Delta Tooltip)")

    try:
        df_sorted = df_display.sort_values("timestamp")
        last7 = df_sorted.tail(24 * 7)

        if last7.empty:
            last7 = df_sorted.copy()

        fig_trend = gradient_line_with_delta(last7)
        st.plotly_chart(fig_trend, use_container_width=True)

    except Exception as e:
        st.error(f"Trend plot error: {e}")

    st.markdown("---")
    st.subheader("🧮 Forecast MCP (Select Model & Horizon)")

    left, right = st.columns([3, 1])
    with left:
        model = st.selectbox("Prediction Model",
                             ["ensemble", "lightgbm", "xgboost", "random_forest", "sarimax"])
        horizon = st.slider("Forecast days", 1, 7, 1)

    with right:
        run_forecast = st.button("Run Forecast", use_container_width=True)

    if run_forecast:
        payload = {
            "data": sanitize_df_for_json(df),
            "horizon_days": int(horizon),
            "model_name": model
        }

        API = st.secrets.get("API_BASE", "")
        if not API:
            st.error("Backend API_BASE not found in Streamlit secrets.")
            st.stop()

        try:
            with st.spinner("Running backend forecast..."):
                r = requests.post(f"{API}/predict/", json=payload, timeout=60)
                r.raise_for_status()

                forecast_df = pd.DataFrame(r.json().get("forecast", []))
                forecast_df["timestamp"] = pd.to_datetime(forecast_df["timestamp"], errors="coerce")

                st.success(f"Forecast ready: {len(forecast_df)} points")
                st.plotly_chart(gradient_line_with_delta(forecast_df),
                                use_container_width=True)

        except Exception as e:
            st.error(f"Forecast error: {e}")


# ============================================
#   TAB 2: HOURLY HEATMAP
# ============================================
with tabs[1]:
    st.subheader("🔥 Heatmap — Hour of Day vs Date")

    try:
        fig_heat = heatmap_hour_by_date(df)
        st.plotly_chart(fig_heat, use_container_width=True)
    except Exception as e:
        st.error(f"Heatmap error: {e}")


# ============================================
#   TAB 3: DAILY PROFILES + HISTOGRAM
# ============================================
with tabs[2]:
    st.subheader("📊 Daily Hourly Profile Comparison")

    normalize = st.checkbox("Normalize each day's profile (0–1)", value=False)

    try:
        fig_profile = daily_profile_comparison(df, normalize=normalize)
        st.plotly_chart(fig_profile, use_container_width=True)
    except Exception as e:
        st.error(f"Daily profile error: {e}")

    st.markdown("---")
    st.subheader("📉 MCP Distribution Histogram")

    try:
        fig_hist = mcp_histogram(df)
        st.plotly_chart(fig_hist, use_container_width=True)
    except Exception as e:
        st.error(f"Histogram error: {e}")


# -----------------------------
#  FOOTER
# -----------------------------
st.caption("Upload data once in the sidebar — visual analytics is applied across all modules.")
