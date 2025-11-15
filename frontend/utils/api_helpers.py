# frontend/utils/api_helpers.py
import pandas as pd
import numpy as np

def sanitize_df_for_json(df):
    """
    Convert pandas DataFrame to JSON-safe list-of-dicts.
    - Convert timestamp -> "YYYY-MM-DD HH:MM:SS"
    - Convert numpy numbers -> native Python int/float
    - Replace NaN/NaT with None
    """
    df2 = df.copy()

    # Timestamp conversion
    if "timestamp" in df2.columns:
        try:
            df2["timestamp"] = pd.to_datetime(df2["timestamp"], errors="coerce")
            df2["timestamp"] = df2["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            df2["timestamp"] = df2["timestamp"].astype(str)

    for col in df2.columns:
        if pd.api.types.is_numeric_dtype(df2[col]):
            df2[col] = pd.to_numeric(df2[col], errors="coerce")
            # convert to python scalars, keep ints as ints if whole
            def to_scalar(x):
                if pd.isna(x):
                    return None
                try:
                    xf = float(x)
                    if xf.is_integer():
                        return int(xf)
                    return float(xf)
                except Exception:
                    return None
            df2[col] = df2[col].apply(to_scalar)
        else:
            # convert NaN/NaT to None and ensure strings
            df2[col] = df2[col].astype(str).replace({"nan": None, "NaT": None, "None": None})
            df2[col] = df2[col].apply(lambda x: None if x in [None, "None", "nan", "NaT"] else x)

    df2 = df2.where(pd.notnull(df2), None)
    return df2.to_dict(orient="records")
