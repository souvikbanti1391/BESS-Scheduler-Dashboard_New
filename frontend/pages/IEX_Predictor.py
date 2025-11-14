import streamlit as st
import pandas as pd
import requests
from utils.plot_helpers import plot_last_7days, plot_forecast

st.title("IEX MCP Predictor")

API = st.secrets.get("API_BASE")

# -------------------------
# USE GLOBAL UPLOADED FILE
# -------------------------
df = st.session_state.get("uploaded_df")

if df is None:
    st.warning("⚠️ Please upload MCP data from the sidebar first.")
    st.stop()

st.success("Using globally uploaded MCP file.")
st.plotly_chart(plot_last_7days(df))

# Prediction options
horizon = st.slider("Forecast days", 1, 7, 1)
model = st.selectbox("Prediction model", ["ensemble", "lightgbm", "xgboost", "random_forest", "sarimax"])

if st.button("Run Forecast"):
    payload = {
        "data": df.to_dict(orient="records"),
        "horizon_days": horizon,
        "model_name": model
    }
    r = requests.post(f"{API}/predict/", json=payload)
    fc = pd.DataFrame(r.json().get("forecast", []))
    st.plotly_chart(plot_forecast(fc))
