import os, pickle
import pandas as pd
import numpy as np

class EnsembleEngine:
    def __init__(self, models_dir='backend/models'):
        self.models_dir = models_dir
        self.models = {}
        self._load_placeholders()

    def _load_placeholders(self):
        # Load available pickles; placeholder models return simple mean forecast
        for name in ['lightgbm','xgboost','random_forest','sarimax']:
            path = os.path.join(self.models_dir, f"{name}.pkl")
            if os.path.exists(path):
                try:
                    with open(path,'rb') as f:
                        self.models[name] = pickle.load(f)
                except Exception:
                    self.models[name] = None
            else:
                self.models[name] = None

    def _naive_forecast(self, df, h):
        last_mean = df['mcp'].dropna().tail(24).mean() if 'mcp' in df.columns else 0.0
        return [float(last_mean) + float(np.random.uniform(-2,2)) for _ in range(h*24)]

    def forecast(self, df, horizon_days, model_name='ensemble'):
        h = int(horizon_days)
        periods = h*24
        # simple index
        last_ts = pd.to_datetime(df['timestamp']).max()
        idx = pd.date_range(last_ts + pd.Timedelta(hours=1), periods=periods, freq='H')
        if model_name in self.models and self.models[model_name] is not None:
            # placeholder: models not actually used in this demo
            preds = self._naive_forecast(df, h)
        else:
            preds = self._naive_forecast(df, h)
        return pd.DataFrame({'timestamp': idx, 'mcp': preds})
