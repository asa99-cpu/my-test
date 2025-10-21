import streamlit as st
from utils import filter_by_date

st.header("🗓️ Filter by Date")

if "df" not in st.session_state or not st.session_state.dt_cols:
    st.warning("No date column found or no data loaded.")
else:
    df = st.session_state.df
    date_col = st.selectbox("Select date column", st.session_state.dt_cols)
    filtered, start, end = filter_by_date(df, date_col)
    st.session_state.filtered_df = filtered
    st.success(f"Showing {len(filtered):,} rows from {start.date()} to {end.date()}.")
    st.dataframe(filtered, use_container_width=True)
