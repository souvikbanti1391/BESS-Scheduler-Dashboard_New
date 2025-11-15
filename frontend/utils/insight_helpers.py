# frontend/utils/insight_helpers.py
import pandas as pd
import numpy as np

def prepare_df(df):
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['mcp'] = pd.to_numeric(df['mcp'], errors='coerce')

    df = df.dropna(subset=['timestamp', 'mcp']).sort_values('timestamp').reset_index(drop=True)

    # Scale Rs/MWh -> Rs/kWh if required
    if df['mcp'].max() > 100:
        df['mcp'] = df['mcp'] / 1000.0

    df['hour'] = df['timestamp'].dt.hour
    df['weekday'] = df['timestamp'].dt.weekday
    df['is_weekend'] = df['weekday'] >= 5
    df['delta'] = df['mcp'].diff().fillna(0.0)
    return df

def compute_insights(df):
    df = prepare_df(df)

    if df.empty:
        return {
            "highest": (0.0, None),
            "lowest": (0.0, None),
            "avg": 0.0,
            "median": 0.0,
            "std": 0.0,
            "peak_hour": 0,
            "cheapest_hour": 0,
            "weekday_avg": 0.0,
            "weekend_avg": 0.0,
            "trend": "N/A",
            "spikes": 0
        }

    highest_row = df.loc[df['mcp'].idxmax()]
    lowest_row = df.loc[df['mcp'].idxmin()]

    avg = float(df['mcp'].mean())
    median = float(df['mcp'].median())
    std = float(df['mcp'].std())

    hourly_mean = df.groupby('hour')['mcp'].mean()
    peak_hour = int(hourly_mean.idxmax()) if not hourly_mean.empty else 0
    cheapest_hour = int(hourly_mean.idxmin()) if not hourly_mean.empty else 0

    weekday_avg = float(df.loc[df['is_weekend'] == False, 'mcp'].mean()) if not df.loc[df['is_weekend'] == False].empty else float('nan')
    weekend_avg = float(df.loc[df['is_weekend'] == True, 'mcp'].mean()) if not df.loc[df['is_weekend'] == True].empty else float('nan')

    # Trend based on last 48 points (if available)
    if len(df) >= 2:
        sample = df['mcp'].tail(48)
        trend = "Up" if sample.iloc[-1] > sample.iloc[0] else "Down"
    else:
        trend = "N/A"

    spikes = int((df['delta'].abs() > (0.15 * max(1e-9, avg))).sum())

    return {
        "highest": (float(highest_row['mcp']), str(highest_row['timestamp'])),
        "lowest": (float(lowest_row['mcp']), str(lowest_row['timestamp'])),
        "avg": avg,
        "median": median,
        "std": std,
        "peak_hour": peak_hour,
        "cheapest_hour": cheapest_hour,
        "weekday_avg": weekday_avg,
        "weekend_avg": weekend_avg,
        "trend": trend,
        "spikes": spikes
    }
