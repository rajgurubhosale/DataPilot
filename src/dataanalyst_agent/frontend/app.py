import streamlit as st
import pandas as pd
from dataanalyst_agent.frontend.api import send_data_to_backend, create_dashboard

st.set_page_config(page_title="AutoAnalyst", page_icon="📊", layout="wide")
st.title("📊 AutoAnalyst")
st.caption("Upload a CSV and get instant insights.")

file = st.file_uploader("Upload your CSV file", type=["csv"], max_upload_size=25)

if file and st.button("📤 Upload & Inspect Data"):
    with st.spinner("Uploading and analyzing schema..."):
        data = send_data_to_backend(file)
        if data:
            st.session_state["analysis"] = data
            st.session_state["run_id"] = data["run_id"]
            st.success(f"Dataset '{file.name}' uploaded successfully! ({data['rows']:,} rows, {data['columns']} columns)")

if "analysis" in st.session_state:
    data = st.session_state["analysis"]
    run_id = st.session_state["run_id"]

    st.divider()
    st.page_link("pages/basic_analysis.py", label="📋 View Dataset Profile & Summary", icon="📋")
    
    columns = [col["column"] for col in data.get("profile", [])]
    target_column = st.selectbox("Select the target column to analyze:", options=columns)

    if st.button("🚀 Perform Data Analysis"):
        with st.spinner("Running AI analysis pipeline across Docker (~45s)..."):
            dashboard = create_dashboard(target_column=target_column, run_id=run_id)
            if dashboard:
                st.session_state["dashboard"] = dashboard
                st.session_state["target_column"] = target_column
                st.success("Analysis complete!")
                st.switch_page("pages/dashboard.py")
