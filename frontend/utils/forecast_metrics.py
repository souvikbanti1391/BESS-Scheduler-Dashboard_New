# frontend/utils/forecast_metrics.py
# Lightweight forecast metrics (no SciPy, no scikit-learn)

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from math import isnan

def compute_forecast_metrics(history_df, forecast_df, actual_df=None):
    """
    If actual_df supplied and overlaps forecast timestamps, compute MAE, RMSE, MAPE, Bias.
    Otherwise return proxy estimates based on recent volatility.
    """
    res = {}
    forecast = forecast_df.copy()
    forecast["timestamp"] = pd.to_datetime(forecast["timestamp"], errors="coerce")
    forecast["mcp"] = pd.to_numeric(forecast["mcp"], errors="coerce")

    if actual_df is not None and not actual_df.empty:
        actual = actual_df.copy()
        actual["timestamp"] = pd.to_datetime(actual["timestamp"], errors="coerce")
        actual["mcp"] = pd.to_numeric(actual["mcp"], errors="coerce")
        merged = pd.merge(forecast, actual, on="timestamp", suffixes=("_pred", "_act"))
        if not merged.empty:
            merged["err"] = merged["mcp_act"] - merged["mcp_pred"]
            merged["abs_err"] = merged["err"].abs()
            merged["pct_err"] = np.where(merged["mcp_act"] != 0, merged["abs_err"] / merged["mcp_act"] * 100.0, np.nan)
            mae = float(merged["abs_err"].mean())
            rmse = float(np.sqrt((merged["err"] ** 2).mean()))
            mape = float(np.nanmean(merged["pct_err"]))
            bias = float(merged["err"].mean())
            res.update({"MAE": mae, "RMSE": rmse, "MAPE": mape, "Bias": bias, "n": len(merged)})
        else:
            res.update({"MAE": np.nan, "RMSE": np.nan, "MAPE": np.nan, "Bias": np.nan, "n": 0})
    else:
        hist = history_df.copy()
        hist["mcp"] = pd.to_numeric(hist["mcp"], errors="coerce")
        recent = hist.tail(24 * 7)
        sigma = float(recent["mcp"].diff().std()) if not recent.empty else float(hist["mcp"].diff().std() if not hist.empty else 0.0)
        res.update({"MAE": float(0.8 * sigma) if sigma else float(np.nan), "RMSE": float(sigma) if sigma else float(np.nan), "MAPE": float(np.nan), "Bias": float(np.nan), "n": len(forecast)})
    return res

def make_error_histograms(df):
    import plotly.subplots as psub
    fig = psub.make_subplots(rows=1, cols=2, subplot_titles=("Absolute Error (Rs/kWh)", "Percentage Error (%)"))
    if "abs_err" in df.columns:
        fig.add_trace(px.histogram(df, x="abs_err", nbins=30).data[0], row=1, col=1)
    if "pct_err" in df.columns:
        fig.add_trace(px.histogram(df, x="pct_err", nbins=30).data[0], row=1, col=2)
    fig.update_layout(template="plotly_dark", height=380)
    return fig

def plot_error_distribution(actual_vs_pred_df):
    df = actual_vs_pred_df.copy()
    if "abs_err" not in df.columns and "err" in df.columns:
        df["abs_err"] = df["err"].abs()
    if "pct_err" not in df.columns and "mcp_act" in df.columns and "abs_err" in df.columns:
        df["pct_err"] = np.where(df["mcp_act"] != 0, (df["abs_err"] / df["mcp_act"]) * 100.0, np.nan)
    fig = make_error_histograms(df)
    return fig

def metric_cards_data(metrics_dict):
    mae = metrics_dict.get("MAE", np.nan)
    rmse = metrics_dict.get("RMSE", np.nan)
    mape = metrics_dict.get("MAPE", np.nan)
    bias = metrics_dict.get("Bias", np.nan)
    cards = [
        {"title": "MAE (Rs/kWh)", "value": f"{mae:.3f}" if not isnan(mae) else "N/A"},
        {"title": "RMSE (Rs/kWh)", "value": f"{rmse:.3f}" if not isnan(rmse) else "N/A"},
        {"title": "MAPE (%)", "value": f"{mape:.2f}%" if not isnan(mape) else "N/A"},
        {"title": "Bias (Rs/kWh)", "value": f"{bias:.3f}" if not isnan(bias) else "N/A"},
    ]
    return cards

def compute_confidence_from_history(history_df, forecast_df, ci=0.9):
    hist = history_df.copy()
    hist["mcp"] = pd.to_numeric(hist["mcp"], errors="coerce")
    recent = hist.tail(24 * 7)
    sigma = float(recent["mcp"].diff().std()) if not recent.empty else float(hist["mcp"].diff().std() if not hist.empty else 0.0)
    if sigma == 0 or np.isnan(sigma):
        return float('nan')
    # approximate CI width ~ 2 * z * sigma
    if ci >= 0.95:
        z = 1.96
    elif ci >= 0.90:
        z = 1.645
    else:
        z = 1.28
    return float(2.0 * z * sigma)
