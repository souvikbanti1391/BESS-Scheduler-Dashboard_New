# frontend/utils/api_helpers.py

import pandas as pd
import numpy as np

def sanitize_df_for_json(df):
    """
    Convert a pandas DataFrame into a JSON-safe list-of-dicts.
    Fixes:
    - Timestamps -> ISO strings
    - numpy types -> python scalars
    - NaN/NaT -> None
    """
    df2 = df.copy()

    # 1. Timestamp -> ISO string
    if "timestamp" in df2.columns:
        try:
            df2["timestamp"] = pd.to_datetime(df2["timestamp"], errors="coerce")
            df2["timestamp"] = df2["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            df2["timestamp"] = df2["timestamp"].astype(str)

    # 2. Convert all numeric dtypes to python numbers
    for col in df2.columns:
        if pd.api.types.is_numeric_dtype(df2[col]):
            df2[col] = pd.to_numeric(df2[col], errors="coerce")
            df2[col] = df2[col].apply(
                lambda x: None if pd.isna(x) else (int(x) if float(x).is_integer() else float(x))
            )
        else:
            # For non-numeric, ensure strings but convert 'nan','None' -> None
            df2[col] = df2[col].astype(str)
            df2[col] = df2[col].apply(
                lambda x: None if x.strip().lower() in ["nan","none","nat"] else x
            )

    df2 = df2.where(pd.notnull(df2), None)

    return df2.to_dict(orient="records")
