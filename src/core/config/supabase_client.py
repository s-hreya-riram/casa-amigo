from supabase import create_client, Client
from requests.exceptions import RequestException
from typing import Optional
import os
from dotenv import load_dotenv
import streamlit as st


# ----------------- Custom Exceptions -----------------
class SupabaseError(Exception):
    """Base exception for Supabase-related errors."""


class SupabaseCredentialsError(SupabaseError):
    """Raised when Supabase credentials are missing or invalid."""


class SupabaseConnectionError(SupabaseError):
    """Raised when unable to connect to Supabase service."""


# ----------------- Supabase Client Wrapper -----------------
class SupabaseClient:
    """Wrapper for Supabase client with robust credential handling."""

    def __init__(self):
        self.client: Optional[Client] = None
        self._init_client()

    def _init_client(self):
        """Initialize Supabase client using Streamlit secrets or .env fallback."""

        load_dotenv()
        url = st.secrets["supabase"]["url"] or os.getenv("SUPABASE_URL")
        key = st.secrets["supabase"]["anon_key"] or os.getenv("SUPABASE_ANON_KEY")


        # --- Validate credentials ---
        if not url or not key:
            raise SupabaseCredentialsError("Supabase URL or key is missing or invalid.")

        # --- Initialize client ---
        try:
            self.client = create_client(url, key)
            self._test_connection()
        except (TypeError, ValueError) as e:
            raise SupabaseCredentialsError(f"Supabase URL or key invalid: {e}") from e
        except RequestException as e:
            raise SupabaseConnectionError(f"Failed to connect to Supabase service: {e}") from e
        except Exception as e:
            raise SupabaseConnectionError(f"Unexpected error initializing Supabase client: {e}") from e

    def _test_connection(self):
        """Optional simple test query to verify connectivity."""
        if not self.client:
            raise SupabaseConnectionError("Supabase client not initialized.")

        try:
            # This ensures the client can communicate with Supabase
            self.client.auth.get_user()
        except RequestException as e:
            raise SupabaseConnectionError("Supabase client created but connection test failed.") from e
        except Exception as e:
            raise SupabaseConnectionError(f"Unexpected error during Supabase connection test: {e}") from e
