import pandas as pd
import io
import re

def _s(x):
    try: return str(x).strip().lower()
    except: return ""

def _series(df, idx):
    return df.iloc[:, idx]

def load_any(uploaded):
    if isinstance(uploaded, pd.DataFrame): return uploaded.copy()
    if hasattr(uploaded, "read"):
        data = uploaded.read()
        bio = io.BytesIO(data)
        name = getattr(uploaded, "name", "").lower()
        if name.endswith(".csv"): return pd.read_csv(io.BytesIO(data))
        if name.endswith((".xls", ".xlsx")): return pd.read_excel(io.BytesIO(data), header=None)
        try: return pd.read_csv(io.BytesIO(data))
        except: pass
        try: return pd.read_excel(io.BytesIO(data), header=None)
        except: pass
        raise ValueError("Upload CSV or Excel.")
    if isinstance(uploaded, str):
        if uploaded.lower().endswith(".csv"): return pd.read_csv(uploaded)
        if uploaded.lower().endswith((".xls", ".xlsx")): return pd.read_excel(uploaded, header=None)
    raise ValueError("Unsupported input.")

def detect_header(df):
    keys = {"date","time","hour","block","mcp","price","datetime"}
    for i in range(min(20,len(df))):
        row = " ".join(_s(v) for v in df.iloc[i])
        if any(k in row for k in keys):
            df.columns = df.iloc[i]
            return df.drop(index=list(range(i+1))).reset_index(drop=True)
    df.columns = df.iloc[0]
    return df.drop(index=[0]).reset_index(drop=True)

def parse_date(col):
    try: return pd.to_datetime(col, errors='coerce')
    except: return pd.Series([pd.NaT]*len(col))

def parse_hour(col):
    s = col.astype(str).str.extract(r"(\d{1,2})")[0]
    try: return s.fillna('0').astype(int)
    except: return pd.Series([0]*len(col))

def parse_timeblock(col):
    s = col.astype(str).str.extract(r"(\d{1,2}:\d{2})")[0]
    if s.isna().all(): return None
    return s.fillna('00:00')

def detect_timestamp(df):
    ncols = df.shape[1]
    for i in range(ncols):
        ser = _series(df,i)
        try:
            dt = pd.to_datetime(ser, errors='coerce')
            if dt.notna().sum() > 5: return dt
        except: pass
    date_idx=None; hour_idx=None
    for i in range(ncols):
        name=_s(df.columns[i])
        if 'date' in name or 'datetime' in name or name=='dt': date_idx=i
        if 'hour' in name or name.startswith('hr'): hour_idx=i
    if date_idx is not None and hour_idx is not None:
        d = parse_date(_series(df,date_idx))
        h = parse_hour(_series(df,hour_idx))
        ts = d + pd.to_timedelta(h-1, unit='h')
        if ts.notna().sum()>5: return ts
    tb_idx=None
    if date_idx is None:
        for i in range(ncols):
            if 'date' in _s(df.columns[i]): date_idx=i; break
    for i in range(ncols):
        if 'block' in _s(df.columns[i]) or ('time' in _s(df.columns[i]) and 'date' not in _s(df.columns[i])):
            tb_idx=i; break
    if date_idx is not None and tb_idx is not None:
        d = parse_date(_series(df,date_idx))
        t = parse_timeblock(_series(df,tb_idx))
        if t is not None:
            ts = pd.to_datetime(d.dt.strftime('%Y-%m-%d') + ' ' + t, errors='coerce')
            if ts.notna().sum()>5: return ts
    for i in range(ncols):
        ser = _series(df,i)
        if pd.api.types.is_numeric_dtype(ser):
            try:
                dt = pd.to_datetime(ser, origin='1899-12-30', unit='D', errors='coerce')
                if dt.notna().sum()>5: return dt
            except: pass
    return pd.date_range('2025-01-01', periods=len(df), freq='H')

def detect_price(df):
    keys=['mcp','price','rs','inr','rate','market clearing']
    candidates=[]; n=len(df); thr=max(3,int(n*0.05))
    for i in range(df.shape[1]):
        lname=_s(df.columns[i]); ser=_series(df,i)
        direct=pd.to_numeric(ser, errors='coerce')
        if direct.notna().sum()>=thr:
            if any(k in lname for k in keys): return direct
            candidates.append(direct)
        extracted = ser.astype(str).str.extract(r'([0-9]*\.?[0-9]+)')[0]
        extr = pd.to_numeric(extracted, errors='coerce')
        if extr.notna().sum()>=thr:
            if any(k in lname for k in keys): return extr
            candidates.append(extr)
    if candidates:
        return max(candidates, key=lambda x: x.var())
    raise ValueError('No numeric price/MCP column detected.')

def validate_and_standardize(uploaded):
    df = load_any(uploaded)
    if any('unnamed' in _s(c) for c in df.columns) or not all(isinstance(c,str) for c in df.columns):
        df = detect_header(df)
    ts = detect_timestamp(df)
    price = detect_price(df)
    out = pd.DataFrame({'timestamp': ts, 'mcp': price})
    out = out.dropna().sort_values('timestamp').reset_index(drop=True)
    return out
