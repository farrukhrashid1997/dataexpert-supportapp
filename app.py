import psycopg2
import streamlit as st
from databricks.sdk import WorkspaceClient

st.title("Lakebase Connection Test")

try:
    w = WorkspaceClient()  # auto-authenticates using DATABRICKS_CLIENT_ID/SECRET from env
    lakebase_url = w.dbutils.secrets.get(scope="database", key="lakebase-url")
    
    conn = psycopg2.connect(lakebase_url)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()
    st.success("✅ Connected to Lakebase!")
    st.write("Postgres version:", version[0])
    cur.close()
    conn.close()
except Exception as e:
    st.error(f"Failed: {e}")