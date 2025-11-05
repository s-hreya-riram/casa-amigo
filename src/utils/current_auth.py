import streamlit as st
from typing import Dict, Any

# NOTE: The global _current_auth dictionary is removed.

def set_current_auth(auth: Dict[str, Any] | None):
    """
    Sets the current authentication data directly into Streamlit's session state.
    This links the Streamlit app's state (st.session_state['auth']) 
    to the state used by your tools (via get_current_auth).
    """
    if auth is None:
        auth = {"token": None, "user_id": None, "email": None, "logged_in": False}
        
    # Always ensure the 'auth' key exists in session_state
    st.session_state["auth"] = dict(auth)

def get_current_auth() -> Dict[str, Any]:
    """
    Retrieves the current authentication data from Streamlit's session state.
    """
    # Safely return the 'auth' dict, or an empty/default dict if not found.
    return dict(st.session_state.get("auth", {
        "token": None, 
        "user_id": None, 
        "email": None, 
        "logged_in": False
    }))