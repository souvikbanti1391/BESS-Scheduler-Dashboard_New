# frontend/pages/BESS_Scheduler.py

import streamlit as st
import pandas as pd
import requests

from utils.api_helpers import sanitize_df_for_json

st.title("BESS Scheduler")

df = st.session_state.get("uploaded_df")

if df is None:
    st.warning("⚠️ Please upload MCP data from the sidebar first.")
    st.stop()

st.success("Using globally uploaded MCP data")

API = st.secrets.get("API_BASE")

# User inputs
power = st.number_input("BESS Power (MW)", 1.0)
energy = st.number_input("BESS Energy (MWh)", 1.0)
horizon = st.slider("Optimisation Horizon (days)", 1, 7, 1)

# -------------------------
# RUN SCHEDULER
# -------------------------
if st.button("Run Scheduler"):

    payload = {
        "data": sanitize_df_for_json(df),
        "bess_power": float(power),
        "bess_energy": float(energy),
        "horizon_days": int(horizon)
    }

    try:
        with st.spinner("Running optimisation..."):
            r = requests.post(f"{API}/schedule/", json=payload, timeout=60)
            r.raise_for_status()

            out = pd.DataFrame(r.json().get("schedule", []))

            if "timestamp" in out.columns:
                out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")

            st.subheader("Optimised BESS Schedule")
            st.dataframe(out)

    except requests.exceptions.RequestException as ex:
        st.error(f"Request error: {ex}")
    except Exception as ex:
        st.error(f"Unexpected error: {ex}")
