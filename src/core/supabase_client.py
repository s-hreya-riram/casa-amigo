import streamlit as st
from supabase import create_client, Client
from requests.exceptions import RequestException
from typing import Optional

# ----------------- Custom Exceptions -----------------
class SupabaseError(Exception):
    """Base exception for Supabase-related errors."""

class SupabaseCredentialsError(SupabaseError):
    """Raised when Supabase credentials are missing or invalid."""

class SupabaseConnectionError(SupabaseError):
    """Raised when unable to connect to Supabase service."""

# ----------------- Supabase Client Wrapper -----------------
class SupabaseClient:
    def __init__(self):
        self.client: Optional[Client] = None
        self._init_client()

    def _init_client(self):
        """Initialize Supabase client with robust, specific error handling."""
        # --- Validate secrets ---
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["anon_key"]
        except KeyError:
            raise SupabaseCredentialsError(
                "Supabase credentials not found in Streamlit secrets."
            )

        if not url or not key:
            raise SupabaseCredentialsError(
                "Supabase URL or key is missing or invalid."
            )

        # --- Create client ---
        try:
            self.client = create_client(url, key)
            self._test_connection()
        except (TypeError, ValueError) as e:
            raise SupabaseCredentialsError(
                f"Supabase URL or key invalid: {e}"
            ) from e
        except RequestException as e:
            raise SupabaseConnectionError(
                f"Failed to connect to Supabase service: {e}"
            ) from e

    def _test_connection(self):
        """Optional simple test query to verify connectivity."""
        try:
            self.client.auth.get_user()
        except RequestException as e:
            raise SupabaseConnectionError(
                "Supabase client created but connection test failed."
            ) from e

