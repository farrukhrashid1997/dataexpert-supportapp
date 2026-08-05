import os

import psycopg2
import streamlit as st

st.title("Lakebase Connection Test")

# Try the resource-injected env var first (adjust key name if needed)
lakebase_url = os.environ.get("lakebase-url") or os.environ.get("LAKEBASE_URL")


st.title("Env Var Debug")
st.json({k: v for k, v in sorted(os.environ.items())})

if not lakebase_url:
    st.error("Could not find lakebase-url in environment variables.")
    st.write("Available env vars (for debugging):")
    st.json({k: v for k, v in os.environ.items() if "lake" in k.lower() or "database" in k.lower() or "pg" in k.lower()})
else:
    try:
        conn = psycopg2.connect(lakebase_url)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        st.success("✅ Connected to Lakebase!")
        st.write("Postgres version:", version[0])
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"Connection failed: {e}")
        
        