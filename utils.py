import pandas as pd
import numpy as np
import streamlit as st
from typing import Optional, List, Tuple

@st.cache_data(show_spinner=False)
def read_csv_safely(file_or_path) -> Optional[pd.DataFrame]:
    try:
        df = pd.read_csv(file_or_path)
        for col in df.columns:
            if col.lower() in ("date", "time", "timestamp", "datetime"):
                df[col] = pd.to_datetime(df[col], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        return None

@st.cache_data(show_spinner=False)
def demo_weather() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=120, freq="D")
    x = np.arange(len(dates))
    return pd.DataFrame({
        "Date": dates,
        "TempC": 12 + 8 * np.sin(x / 9) + np.random.normal(0, 1.3, len(dates)),
        "Rain_mm": np.clip(np.random.gamma(1.5, 1.2, len(dates)) - 1.2, 0, None),
        "Wind_kmh": 10 + np.random.normal(0, 3, len(dates)),
    })

def find_datetime_columns(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]

def numeric_columns(df: pd.DataFrame) -> List[str]:
    return df.select_dtypes(include="number").columns.tolist()

def filter_by_date(df: pd.DataFrame, date_col: str) -> Tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    dmin, dmax = df[date_col].min(), df[date_col].max()
    start, end = st.date_input("Date range", value=(dmin.date(), dmax.date()))
    mask = (df[date_col] >= pd.to_datetime(start)) & (df[date_col] <= pd.to_datetime(end))
    return df.loc[mask].copy(), pd.to_datetime(start), pd.to_datetime(end)

def resample_df(df, date_col, cols, freq, how):
    if not freq:
        return df.set_index(date_col)[cols].sort_index()
    agg = "mean" if how == "Mean" else "sum"
    return df.set_index(date_col)[cols].sort_index().resample(freq).agg(agg)

def apply_rolling(df, window): return df.rolling(window, min_periods=1).mean() if window > 1 else df
def normalize_01(df): return (df - df.min()) / (df.max() - df.min())
