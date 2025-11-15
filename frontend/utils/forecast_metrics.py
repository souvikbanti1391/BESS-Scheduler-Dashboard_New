# frontend/utils/forecast_metrics.py
# ============================================================
# Forecast metrics helpers
# - compute_forecast_metrics: computes MAE, RMSE, MAPE, Bias, coverage if actuals available
# - plot_error_distribution: histogram of errors
# - metric_cards_data: prepare numeric summary for display
# - compute_confidence_from_history: helper for CI estimation fallback
# ============================================================

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from math import isnan

def safe_mean(x):
    try:
        return float(np.nanmean(x))
    except:
        return float('nan')

def compute_forecast_metrics(history_df, forecast_df, actual_df=None):
    """
    history_df: historical data (for uncertainty estimation)
    forecast_df: predictions with 'timestamp' and 'mcp'
    actual_df: if available, actual observed MCPs for the forecast period (same timestamps)
    Returns: dict with MAE, RMSE, MAPE, bias (mean error), coverage_estimate (if actuals)
    """
    res = {}
    forecast = forecast_df.copy()
    forecast["timestamp"] = pd.to_datetime(forecast["timestamp"], errors="coerce")
    forecast["mcp"] = pd.to_numeric(forecast["mcp"], errors="coerce")

    # If actuals provided and timestamps overlap, compute error metrics.
    if actual_df is not None:
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
        # No actuals => use historical volatility to generate a proxy of uncertainty
        # Use last 7 days history std of delta as proxy
        hist = history_df.copy()
        hist["mcp"] = pd.to_numeric(hist["mcp"], errors="coerce")
        recent = hist.tail(24 * 7)
        sigma = float(recent["mcp"].diff().std()) if not recent.empty else float(hist["mcp"].diff().std() if not hist.empty else 0.0)
        # Provide approximate RMSE ~ sigma, MAE ~ 0.8*sigma (rule of thumb)
        res.update({"MAE": float(0.8 * sigma) if sigma else float(np.nan), "RMSE": float(sigma) if sigma else float(np.nan), "MAPE": float(np.nan), "Bias": float(np.nan), "n": len(forecast)})

    return res


def plot_error_distribution(actual_vs_pred_df):
    """
    actual_vs_pred_df: dataframe with columns ['timestamp','mcp_act','mcp_pred','err','abs_err']
    Returns plotly figure (histogram) of absolute percentage errors and absolute errors
    """
    df = actual_vs_pred_df.copy()
    if "abs_err" not in df.columns and "err" in df.columns:
        df["abs_err"] = df["err"].abs()
    if "pct_err" not in df.columns and "mcp_act" in df.columns and "abs_err" in df.columns:
        df["pct_err"] = np.where(df["mcp_act"] != 0, (df["abs_err"] / df["mcp_act"]) * 100.0, np.nan)

    # two-panel subplot: left absolute error histogram, right % error histogram
    fig = make_error_histograms(df)
    return fig


def make_error_histograms(df):
    import plotly.subplots as psub
    fig = psub.make_subplots(rows=1, cols=2, subplot_titles=("Absolute Error (Rs/kWh)", "Percentage Error (%)"))
    if "abs_err" in df.columns:
        fig.add_trace(px.histogram(df, x="abs_err", nbins=30).data[0], row=1, col=1)
    if "pct_err" in df.columns:
        fig.add_trace(px.histogram(df, x="pct_err", nbins=30).data[0], row=1, col=2)

    fig.update_layout(template="plotly_dark", height=380)
    return fig


def metric_cards_data(metrics_dict):
    """
    Input metrics_dict returned by compute_forecast_metrics.
    Returns a list of card dicts to be rendered on the page.
    """
    # metrics_dict keys: MAE, RMSE, MAPE, Bias, n
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
    """
    Return a simple confidence-width estimate for forecast_df based on history volatility.
    Returns: mean_ci_width (Rs/kWh)
    """
    hist = history_df.copy()
    hist["mcp"] = pd.to_numeric(hist["mcp"], errors="coerce")
    recent = hist.tail(24 * 7)
    sigma = float(recent["mcp"].diff().std()) if not recent.empty else float(hist["mcp"].diff().std() if not hist.empty else 0.0)
    if sigma == 0 or np.isnan(sigma):
        return float('nan')
    z = norm.ppf(0.5 + ci / 2.0)
    # approximate mean width as 2*z*sigma
    return float(2.0 * z * sigma)
