import streamlit as st
from PIL import Image
import os

st.set_page_config(page_title='BESS Optimiser', layout='wide')

# Tiles dashboard
col1, col2, col3 = st.columns(3)
with col1:
    st.image('frontend/assets/dvc_logo.png', width=120)
    st.markdown('### IEX MCP Predictor')
    st.markdown('Upload MCP data, validate and forecast')

with col2:
    st.image('frontend/assets/bess_image.png', width=220)
    st.markdown('### BESS Scheduler')
    st.markdown('Create optimal charging/discharging schedule')

with col3:
    st.markdown('### Reports & Models')
    st.markdown('Generate PDF reports and view model status')

st.title('Welcome to BESS Optimiser (DVC)')
st.write('Use the sidebar to navigate to Predictor, Scheduler, or Reports.')
