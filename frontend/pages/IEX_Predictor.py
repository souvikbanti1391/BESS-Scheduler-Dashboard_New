
# frontend/pages/IEX_Predictor.py

import streamlit as st
import pandas as pd
import requests

from utils.csv_validator import validate_and_standardize
from utils.plot_helpers import plot_last_7days, plot_forecast
from utils.api_helpers import sanitize_df_for_json

st.title("IEX MCP Predictor")

API = st.secrets.get("API_BASE")

# -------------------------
# USE GLOBAL UPLOADED FILE
# -------------------------
df = st.session_state.get("uploaded_df")

if df is None:
    st.warning("⚠️ Please upload MCP data from the sidebar first.")
    st.stop()

st.success("Using globally uploaded MCP data")
st.plotly_chart(plot_last_7days(df))

# Forecast controls
horizon = st.slider("Forecast days", 1, 7, 1)
model = st.selectbox("Select Prediction Model",
                     ["ensemble", "lightgbm", "xgboost", "random_forest", "sarimax"])

# -------------------------
# RUN FORECAST
# -------------------------
if st.button("Run Forecast"):
    df_payload = sanitize_df_for_json(df)

    payload = {
        "data": df_payload,
        "horizon_days": int(horizon),
        "model_name": model
    }

    try:
        with st.spinner("Running forecast..."):
            r = requests.post(f"{API}/predict/", json=payload, timeout=60)
            r.raise_for_status()

            resp = r.json()
            fc = pd.DataFrame(resp.get("forecast", []))

            if fc.empty:
                st.error("⚠️ No forecast returned.")
            else:
                fc["timestamp"] = pd.to_datetime(fc["timestamp"], errors="coerce")
                st.plotly_chart(plot_forecast(fc))

    except requests.exceptions.RequestException as ex:
        st.error(f"Request error: {ex}")
    except Exception as ex:
        st.error(f"Unexpected error: {ex}")
