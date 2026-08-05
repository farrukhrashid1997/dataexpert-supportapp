import streamlit as st

import lakebase

st.title("Lakebase Connection Test")

try:
    result = lakebase.run_query("SELECT version();")
    st.success("✅ Connected to Lakebase!")
    st.write(result)
except Exception as e:
    st.error(f"Failed: {e}")
    st.exception(e)