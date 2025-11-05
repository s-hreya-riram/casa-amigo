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
        """Initialize Supabase client using environment variables as primary source."""

        # 1. Load .env file (good for local testing)
        load_dotenv()
        
        url = None
        key = None

        # 2. Try to get secrets from Streamlit (if the code runs in a Streamlit context)
        # We wrap this in a try block because accessing st.secrets itself can throw the error
        try:
            # We must check if 'st.secrets' is available and has the 'supabase' key
            if "supabase" in st.secrets:
                url = st.secrets["supabase"].get("url")
                key = st.secrets["supabase"].get("anon_key")
        except:
            # If st.secrets isn't initialized (which is the case in FastAPI), ignore this block
            pass 

        # 3. Fallback to Environment Variables (This is your primary source on Render)
        url = url or os.getenv("SUPABASE_URL")
        key = key or os.getenv("SUPABASE_ANON_KEY")

        # --- Validate credentials ---
        if not url or not key:
            raise SupabaseCredentialsError("Supabase URL or key is missing or invalid.")
        
        # --- Initialize client ---
        try:
            self.client = create_client(url, key)
            self._test_connection()
        # ... (rest of your error handling remains the same)
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
