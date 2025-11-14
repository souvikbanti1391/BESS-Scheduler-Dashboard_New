import streamlit as st
import pandas as pd
import requests
from utils.csv_validator import validate_and_standardize
from utils.plot_helpers import plot_last_7days, plot_forecast

st.title('IEX MCP Predictor')
API = st.secrets.get('API_BASE','http://localhost:8000')

file = st.file_uploader('Upload MCP CSV/Excel', type=['csv','xls','xlsx'])

if file:
    try:
        df = validate_and_standardize(file)
        st.success('File validated successfully!')
        st.plotly_chart(plot_last_7days(df))
        horizon = st.slider('Forecast days',1,7,1)
        model = st.selectbox('Model',['ensemble','lightgbm','xgboost','random_forest','sarimax'])
        if st.button('Run Forecast'):
            payload = {'data': df.to_dict(orient='records'),'horizon_days':horizon,'model_name':model}
            r = requests.post(f"{API}/predict/", json=payload, timeout=30)
            fc = pd.DataFrame(r.json().get('forecast',[]))
            st.plotly_chart(plot_forecast(fc))
    except Exception as e:
        st.error(f'Validation error: {e}')
