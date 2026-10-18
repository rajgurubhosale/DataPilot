import streamlit as st
import pandas as pd

st.set_page_config(page_title="AutoAnalyst", page_icon="📊", layout="wide")
st.title("📊 AutoAnalyst")
st.caption("Upload a CSV and get instant insights.")

file = st.file_uploader("Upload your CSV file", type="csv", max_upload_size=25)

if st.button("Perform data analysis"):
    if file:
        st.session_state["df"] = pd.read_csv(file)
        st.switch_page("pages/basic_analysis.py")
    else:
        st.warning("Please upload a CSV file first.")