import pandas as pd
import numpy as np

def prepare_df(df):
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['mcp'] = pd.to_numeric(df['mcp'], errors='coerce')

    df = df.dropna(subset=['timestamp', 'mcp'])
    df = df.sort_values('timestamp')

    # Scale Rs/MWh → Rs/kWh
    if df['mcp'].max() > 100:
        df['mcp'] = df['mcp'] / 1000.0

    df['hour'] = df['timestamp'].dt.hour
    df['weekday'] = df['timestamp'].dt.weekday  # 0=Mon
    df['is_weekend'] = df['weekday'] >= 5
    df['delta'] = df['mcp'].diff().fillna(0)

    return df


def compute_insights(df):
    df = prepare_df(df)

    highest = df.loc[df['mcp'].idxmax()]
    lowest = df.loc[df['mcp'].idxmin()]

    avg = df['mcp'].mean()
    std = df['mcp'].std()
    median = df['mcp'].median()

    # Peak hour based on average per hour
    hourly_mean = df.groupby('hour')['mcp'].mean()
    peak_hour = int(hourly_mean.idxmax())
    cheapest_hour = int(hourly_mean.idxmin())

    # Weekday vs weekend
    weekday_avg = df.loc[df['is_weekend'] == False, 'mcp'].mean()
    weekend_avg = df.loc[df['is_weekend'] == True, 'mcp'].mean()

    # Direction: based on last 48 hours
    trend = df['mcp'].tail(48)
    direction = "Up" if trend.iloc[-1] > trend.iloc[0] else "Down"

    # Spike count (>15% jump)
    spikes = (df['delta'].abs() > (0.15 * avg)).sum()

    return {
        "highest": (highest['mcp'], highest['timestamp']),
        "lowest": (lowest['mcp'], lowest['timestamp']),
        "avg": avg,
        "median": median,
        "std": std,
        "peak_hour": peak_hour,
        "cheapest_hour": cheapest_hour,
        "weekday_avg": weekday_avg,
        "weekend_avg": weekend_avg,
        "trend": direction,
        "spikes": int(spikes)
    }
