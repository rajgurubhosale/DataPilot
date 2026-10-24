import requests
import streamlit as st
BACKEND_URL = "http://localhost:8000/"

def send_data_to_backend(file):

    files = {"file": (file.name, file.getvalue(), "text/csv")}

    try:
        response = requests.post(BACKEND_URL + "upload_data", files=files, timeout=30)
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach backend: {e}")
        return None
    if response.status_code != 200:
        st.error(f"API error {response.status_code}: {response.text}")
        return None 

    return response.json()


def create_dashboard(target_column:str,run_id):
    try:
        payload = {
            'run_id':run_id,
            'target_column':target_column
        }
        response = requests.post(BACKEND_URL + "create_dashboard", json=payload, timeout=300)
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach backend: {e}")
        return None
    if response.status_code != 200:
        st.error(f"API error {response.status_code}: {response.text}")
        return None 

    return response.json()
