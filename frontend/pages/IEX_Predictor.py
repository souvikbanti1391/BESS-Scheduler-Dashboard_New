# frontend/pages/IEX_Predictor.py
# ============================================================
# IEX MCP Predictor — Market-style dashboard (dark theme)
# - Full-width stacked windows: MCP chart, 7-day heatmap
# - Base64-embedded banner + logo (if assets exist in frontend/assets/)
# - Forecast integration: when user runs backend predict, show forecast plot with CI and metrics
# ============================================================

# PATH fix (so utils imports work reliably in Streamlit Cloud)
import sys
from pathlib import Path
CURRENT_DIR = Path(__file__).resolve()
UTILS_DIR = CURRENT_DIR.parent.parent / "utils"
ASSETS_DIR = CURRENT_DIR.parent.parent / "assets"
sys.path.append(str(UTILS_DIR))

import streamlit as st
import pandas as pd
import io
import base64
import os
import requests

from plot_helpers import market_style_line, heatmap_last7_with_bands, plot_forecast_with_ci, prepare_df
from forecast_metrics import compute_forecast_metrics, metric_cards_data, plot_error_distribution, compute_confidence_from_history

st.set_page_config(page_title="BESS Scheduler Intelligence", layout="wide", initial_sidebar_state="expanded")

# ---------------------------
# Helper: embed images as base64 if available
# ---------------------------
def _load_asset_base64(asset_name):
    """
    Attempts to load asset_name from frontend/assets/ or given path.
    Returns data URI (base64) or None
    """
    # try relative path inside repo
    candidates = [
        ASSETS_DIR / asset_name,
        CURRENT_DIR.parent.parent / asset_name,
        Path(asset_name)
    ]
    for p in candidates:
        try:
            if p.exists():
                b = p.read_bytes()
                mime = "image/png" if str(p).lower().endswith((".png", ".jpg", ".jpeg")) else "image/png"
                s = base64.b64encode(b).decode("ascii")
                return f"data:{mime};base64,{s}"
        except Exception:
            continue
    return None

# attempt to load banner and logo (use files you said you uploaded earlier)
banner_b64 = _load_asset_base64("bess_image.png") or _load_asset_base64("bess_image.png.jpg") or _load_asset_base64("bess_image.jpg")
dvc_b64 = _load_asset_base64("dvc_logo.png") or _load_asset_base64("dvc_logo.png.jpg") or _load_asset_base64("dvc_logo.jpg")

# -----------------------------
# Header / Banner (base64 embedded)
# -----------------------------
hero_html = ""
if banner_b64:
    hero_html = f"""
    <style>
    .hero {{
        background-image: linear-gradient(rgba(0,0,0,0.45), rgba(0,0,0,0.45)), url('{banner_b64}');
        background-size: cover;
        background-position: center;
        border-radius: 8px;
        padding: 28px;
        color: #ffffff;
        margin-bottom: 18px;
    }}
    .hero-title {{ font-size:30px; font-weight:700; margin-bottom:4px; }}
    .hero-sub {{ color: rgba(255,255,255,0.85); margin-bottom:8px; }}
    .dvc-logo {{ float: right; height:56px; margin-left:12px; border-radius:6px; }}
    .small-note {{ color: rgba(255,255,255,0.6); font-size:12px; margin-top:8px;}}
    </style>
    <div class="hero">
      {f'<img class="dvc-logo" src="{dvc_b64}" />' if dvc_b64 else ""}
      <div class="hero-title">BESS Scheduler Intelligence</div>
      <div class="hero-sub">Excel through Intelligence</div>
      <div class="small-note">Interactive MCP analytics — full-width charts, smart heatmaps, forecasting with CI & performance metrics.</div>
    </div>
    """
else:
    # fallback simple banner
    hero_html = """
    <div style="padding:18px;border-radius:6px;background-color:#0a0b0f;margin-bottom:12px">
      <div style="display:flex;align-items:center;justify-content:space-between">
        <div>
          <div style="font-size:28px;font-weight:700;color:#fff">BESS Scheduler Intelligence</div>
          <div style="color:rgba(255,255,255,0.8)">Excel through Intelligence</div>
        </div>
        <div>{}</div>
      </div>
    </div>
    """

st.markdown(hero_html, unsafe_allow_html=True)

# -----------------------
# Sidebar: upload + official links mini-panel
# -----------------------
st.sidebar.title("Upload & Links")
st.sidebar.markdown("Upload MCP CSV / XLSX (timestamp + price).")
uploaded = st.sidebar.file_uploader("Choose file", type=["csv", "xlsx", "xls"], accept_multiple_files=False)

st.sidebar.markdown("---")
st.sidebar.markdown("🔗 Official Links")
st.sidebar.markdown(
    """
    <div style="max-height:220px; overflow:auto; padding-right:6px;">
      <a href="https://iexindia.com" target="_blank">• IEX Market Portal</a><br>
      <a href="https://posoco.in" target="_blank">• POSOCO / NLDC</a><br>
      <a href="https://powermin.gov.in" target="_blank">• Ministry of Power</a><br>
      <a href="https://www.dvc.gov.in" target="_blank">• Damodar Valley Corporation (DVC)</a><br>
      <a href="https://cercind.gov.in" target="_blank">• CERC</a><br>
    </div>
    """, unsafe_allow_html=True
)

st.sidebar.markdown("---")
st.sidebar.caption("Tip: Use 1W or 1M selector to zoom. Heatmap shows best charge (blue) and discharge (red) bands.")

# -----------------------
# Load data (global session state)
# -----------------------
if uploaded is not None:
    try:
        if uploaded.name.lower().endswith((".xls", ".xlsx")):
            df = pd.read_excel(uploaded)
        else:
            df = pd.read_csv(uploaded)
        st.session_state["uploaded_df"] = df
        st.sidebar.success("File uploaded and loaded.")
    except Exception as e:
        st.sidebar.error(f"Upload error: {e}")

df = st.session_state.get("uploaded_df")
if df is None:
    st.warning("Please upload MCP CSV/XLSX in the left sidebar to view the dashboard.")
    st.stop()

# Prepare / validate and auto-scale
try:
    df_clean = prepare_df(df)
except Exception as e:
    st.error(f"Data preparation error: {e}")
    st.stop()

# Visualization options
with st.expander("Visualization Options", expanded=False):
    col1, col2 = st.columns([1,1])
    with col1:
        smoothing = st.checkbox("Smooth line (3-pt rolling)", value=True)
        animate = st.checkbox("Enable animated transitions", value=True)
    with col2:
        low_pct = st.slider("Charge band percentile (low)", 1, 40, 20)
        high_pct = st.slider("Discharge band percentile (high)", 60, 99, 80)

# -----------------------
# Full-width stacked windows: Chart then Heatmap
# -----------------------
st.subheader("MCP Time Series")
try:
    fig_market = market_style_line(df_clean, smoothing=smoothing)
    st.plotly_chart(fig_market, use_container_width=True)
except Exception as e:
    st.error(f"Chart rendering error: {e}")

st.markdown("---")
st.subheader("7-Day Charge/Discharge Opportunity")
try:
    fig_hm = heatmap_last7_with_bands(df_clean, low_pct=low_pct, high_pct=high_pct)
    st.plotly_chart(fig_hm, use_container_width=True)
except Exception as e:
    st.error(f"Heatmap rendering error: {e}")

# -----------------------
# Forecast block: model selection + run
# -----------------------
st.markdown("---")
st.subheader("Forecast (1–7 days)")
col1, col2, col3 = st.columns([2,1,1])
with col1:
    model = st.selectbox("Model (backend)", ["ensemble", "lightgbm", "xgboost", "random_forest", "sarimax"])
    horizon = st.slider("Forecast days", 1, 7, 1)
with col2:
    run_forecast = st.button("Run Forecast")
with col3:
    show_metrics = st.checkbox("Show forecast metrics & CI", value=True)

# run forecast: call backend API
if run_forecast:
    API = st.secrets.get("API_BASE", "")
    if not API:
        st.error("Backend API_BASE not found in Streamlit secrets.")
    else:
        payload = {
            "data": df_clean.to_dict(orient="records"),
            "horizon_days": int(horizon),
            "model_name": model
        }
        try:
            with st.spinner("Running backend forecast..."):
                r = requests.post(f"{API}/predict/", json=payload, timeout=90)
                r.raise_for_status()
                resp = r.json()
                forecast_list = resp.get("forecast", [])
                if not forecast_list:
                    st.info("No forecast returned from backend.")
                else:
                    forecast_df = pd.DataFrame(forecast_list)
                    # show forecast plot with CI
                    fig_fc = plot_forecast_with_ci(df_clean, forecast_df, ci=0.9)
                    st.plotly_chart(fig_fc, use_container_width=True)

                    # compute metrics (if we have actuals in the uploaded df for the forecast window)
                    # Attempt to find actuals overlapping forecast timestamps
                    try:
                        # if uploaded contains future actuals (rare), compute errors; else compute proxy metrics
                        actuals = df_clean[df_clean["timestamp"].isin(pd.to_datetime(forecast_df["timestamp"], errors="coerce"))]
                        actuals = actuals[["timestamp", "mcp"]].rename(columns={"mcp": "mcp_act"})
                        # merge to compute actual errors if present
                        merged = None
                        if not actuals.empty:
                            merged = pd.merge(forecast_df.rename(columns={"mcp":"mcp_pred"}), actuals, on="timestamp", how="inner")
                            if not merged.empty:
                                merged["err"] = merged["mcp_act"] - merged["mcp_pred"]
                                merged["abs_err"] = merged["err"].abs()
                                merged["pct_err"] = merged.apply(lambda r: (r["abs_err"]/r["mcp_act"]*100.0) if r["mcp_act"] else None, axis=1)
                        # compute numeric metrics
                        metrics = compute_forecast_metrics(df_clean, forecast_df, actual_df=actuals if not actuals.empty else None)
                        cards = metric_cards_data(metrics)
                    except Exception as e:
                        metrics = compute_forecast_metrics(df_clean, forecast_df, actual_df=None)
                        cards = metric_cards_data(metrics)

                    # display metric cards
                    if show_metrics:
                        st.markdown("#### Forecast Metrics")
                        cols = st.columns(len(cards))
                        for ccol, card in zip(cols, cards):
                            ccol.metric(card["title"], card["value"])

                        # error distribution histogram if we have merged actuals
                        if 'merged' in locals() and merged is not None and not merged.empty:
                            st.markdown("**Error Distribution (actual vs predicted)**")
                            hist_fig = plot_error_distribution(merged.rename(columns={"mcp_act":"mcp_act","mcp_pred":"mcp_pred","err":"err","abs_err":"abs_err","pct_err":"pct_err"}))
                            st.plotly_chart(hist_fig, use_container_width=True)
                        else:
                            # show proxy uncertainty metric visualization using history
                            ci_width = compute_confidence_from_history(df_clean, forecast_df, ci=0.9)
                            st.info(f"Estimated 90% CI width (proxy from history): {ci_width:.3f} Rs/kWh (used when actuals are not available).")

        except Exception as e:
            st.error(f"Forecast API error: {e}")

# Bottom summary & download
st.markdown("---")
c1, c2 = st.columns([3, 1])
with c1:
    st.write(f"**Data range:** {df_clean['timestamp'].min()} → {df_clean['timestamp'].max()}  •  **Rows:** {len(df_clean)}")
    st.write(f"**Avg MCP:** {df_clean['mcp'].mean():.3f} Rs/kWh  •  **Std Dev:** {df_clean['mcp'].std():.3f}")
with c2:
    csv_bytes = df_clean.to_csv(index=False).encode()
    st.download_button("Download cleaned CSV", data=csv_bytes, file_name="mcp_cleaned.csv", mime="text/csv")

st.caption("Tip: Use the range selector (1D / 7D / 1M / All) and the rangeslider to quickly inspect windows. Weekend bands and day labels help spot patterns.")
