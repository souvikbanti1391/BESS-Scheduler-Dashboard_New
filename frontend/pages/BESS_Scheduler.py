import streamlit as st
import pandas as pd
import requests

st.title("BESS Scheduler")

df = st.session_state.get("uploaded_df")

if df is None:
    st.warning("⚠️ Upload MCP data from the sidebar first.")
    st.stop()

st.success("Using globally uploaded MCP data.")

API = st.secrets.get("API_BASE")

power = st.number_input("BESS Power (MW)", 1.0)
energy = st.number_input("BESS Energy (MWh)", 1.0)
horizon = st.slider("Optimisation horizon (days)", 1, 7, 1)

if st.button("Run Scheduler"):
    payload = {
        "data": df.to_dict(orient="records"),
        "bess_power": power,
        "bess_energy": energy,
        "horizon_days": horizon
    }
    r = requests.post(f"{API}/schedule/", json=payload)
    out = pd.DataFrame(r.json().get("schedule", []))
    
    st.subheader("Optimised Schedule")
    st.dataframe(out)
