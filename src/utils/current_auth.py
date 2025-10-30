# utils/current_auth.py

_current_auth: dict = {}

def set_current_auth(auth: dict | None):
    # store a shallow copy so tools can't mutate Streamlit's dict
    global _current_auth
    _current_auth = dict(auth or {})

def get_current_auth() -> dict:
    return dict(_current_auth)
