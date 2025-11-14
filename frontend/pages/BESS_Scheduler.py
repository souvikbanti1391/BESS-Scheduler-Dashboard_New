import streamlit as st
import pandas as pd
from utils.csv_validator import validate_and_standardize
from utils.plot_helpers import plot_forecast

st.title('BESS Scheduler')

file = st.file_uploader('Upload MCP CSV/Excel', type=['csv','xls','xlsx'])

if file:
    df = validate_and_standardize(file)
    st.write('Showing validated data head:')
    st.dataframe(df.head())
    p = st.number_input('BESS Power (MW)', 1.0)
    e = st.number_input('BESS Energy (MWh)', 1.0)
    h = st.slider('Horizon days', 1, 7, 1)
    if st.button('Run Scheduler'):
        import requests, os
        API = st.secrets.get('API_BASE','http://localhost:8000')
        payload = {'data': df.to_dict(orient='records'),'bess_power':p,'bess_energy':e,'horizon_days':h}
        r = requests.post(f"{API}/schedule/", json=payload, timeout=30)
        out = pd.DataFrame(r.json().get('schedule',[]))
        st.dataframe(out)
