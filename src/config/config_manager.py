import os
import streamlit as st
from dotenv import load_dotenv

class ConfigManager:
    """Manages application configuration and environment variables."""
    
    def __init__(self):
        load_dotenv()
        self.api_key = self._load_api_key()
    
    def _load_api_key(self) -> str:
        """Load and validate OpenAI API key from environment or Streamlit secrets."""
        # Try Streamlit secrets first (for deployed apps)
        try:
            api_key = st.secrets["openai"]["api_key"]
            if api_key and api_key.strip() and api_key != "your_openai_api_key_here":
                return api_key.strip()
        except (KeyError, FileNotFoundError, AttributeError):
            pass
        
        # Fall back to environment variable (for local development)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key.strip():
            return api_key.strip()
        
        st.error("🔑 OpenAI API key not found. Please configure it in either:")
        st.error("• .env file (OPENAI_API_KEY=your_key)")
        st.error("• .streamlit/secrets.toml ([openai] api_key='your_key')")
        st.stop()
    
    def get_debug_mode(self) -> bool:
        """Get debug mode setting."""
        # Fall back to environment variable since we simplified secrets.toml
        return os.getenv("DEBUG", "false").lower() == "true"
    
    def get_environment(self) -> str:
        """Get current environment setting."""
        # Fall back to environment variable since we simplified secrets.toml
        return os.getenv("ENVIRONMENT", "development")