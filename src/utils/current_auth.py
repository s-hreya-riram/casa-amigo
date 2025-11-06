# utils/current_auth.py
import streamlit as st

def set_current_auth(auth: dict | None):
    """
    Store auth in Streamlit's session_state (persists across reruns).
    """
    if auth is None:
        auth = {"token": None, "user_id": None, "email": None, "logged_in": False}
    
    # Store in session_state so it survives reruns
    st.session_state["_current_auth"] = dict(auth)
    print(f"[AUTH] Set auth in session_state: user_id={auth.get('user_id')}, has_token={bool(auth.get('token'))}")

def get_current_auth() -> dict:
    """
    Retrieve auth from Streamlit's session_state.
    """
    auth = st.session_state.get("_current_auth", {
        "token": None,
        "user_id": None,
        "email": None,
        "logged_in": False
    })
    print(f"[AUTH] Get auth from session_state: user_id={auth.get('user_id')}, has_token={bool(auth.get('token'))}")
    return dict(auth)