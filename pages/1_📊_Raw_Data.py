import streamlit as st

st.header("📊 Raw Data")

if "df" not in st.session_state:
    st.warning("Please upload a CSV in the main page first.")
else:
    df = st.session_state.df
    st.dataframe(df, use_container_width=True)
