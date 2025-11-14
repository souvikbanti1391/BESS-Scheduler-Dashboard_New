import streamlit as st
from PIL import Image
import os
from utils.csv_validator import validate_and_standardize

st.set_page_config(page_title='BESS Optimiser', layout='wide')

# -------------------------
# GLOBAL SIDEBAR UPLOAD
# -------------------------
st.sidebar.header("📂 Upload MCP File (Global)")

uploaded = st.sidebar.file_uploader(
    "Upload MCP CSV/Excel (one-time upload)",
    type=["csv", "xls", "xlsx"]
)

if uploaded:
    try:
        df = validate_and_standardize(uploaded)
        st.session_state["uploaded_df"] = df
        st.sidebar.success("File uploaded & validated successfully!")
    except Exception as e:
        st.session_state["uploaded_df"] = None
        st.sidebar.error(f"Validation error: {e}")

# -------------------------
# HOME PAGE UI
# -------------------------
st.title("🔋 BESS Optimiser – Dashboard")

logo='frontend/assets/dvc_logo.png'
bess='frontend/assets/bess_image.png'

col1, col2, col3 = st.columns(3)
with col1:
    if os.path.exists(logo):
        st.image(logo, width=120)
    st.markdown("### 🔍 IEX Predictor")
    st.markdown("Predict MCP using ML & ensemble models.")

with col2:
    if os.path.exists(bess):
        st.image(bess, width=200)
    st.markdown("### ⚡ BESS Scheduler")
    st.markdown("Optimise BESS charge/discharge cycles.")

with col3:
    st.markdown("### 📝 PDF Reports")
    st.markdown("Download professional analysis reports.")

st.write("Use the sidebar to upload data only **once**. All sections will use the same dataset.")
