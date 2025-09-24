import os
import streamlit as st
from dotenv import load_dotenv

class ConfigManager:
    """Manages application configuration and environment variables."""
    
    def __init__(self):
        load_dotenv()
        self.api_key = self._load_api_key()
    
    def _load_api_key(self) -> str:
        """Load and validate OpenAI API key from environment."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("OPENAI_API_KEY not found in .env")
            st.stop()
        return api_key