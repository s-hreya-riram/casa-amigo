import os
import base64
import streamlit as st
from dotenv import load_dotenv
from typing import List, Dict, Any

from config import ConfigManager
from core import ChatbotEngine, DocumentIndexManager

class StreamlitApp:
    """Manages the Streamlit UI and user interactions."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.doc_manager = DocumentIndexManager()
        self.chatbot = ChatbotEngine(self.doc_manager.index, self.config_manager.api_key)
        self.logo_base64 = None  # Cache for logo base64 string
        self._setup_page()
        self._initialize_session_state()
    
    def _setup_page(self):
        """Configure Streamlit page settings and title."""
        st.set_page_config(page_title="Casa Amigo Chatbot", page_icon="🏠")

        self._add_logo()
       
        # Show configuration status in sidebar (for debugging)
        if self.config_manager.get_debug_mode():
            with st.sidebar:
                st.subheader("🔧 Configuration Status")
                
                # Check which config method is being used
                try:
                    secrets_key = st.secrets["openai"]["api_key"]
                    if secrets_key and secrets_key != "your_openai_api_key_here":
                        st.success("✅ Using Streamlit secrets")
                    else:
                        st.warning("⚠️ Streamlit secrets not configured")
                except (KeyError, FileNotFoundError):
                    if os.getenv("OPENAI_API_KEY"):
                        st.success("✅ Using environment variable")
                    else:
                        st.error("❌ No API key found")
                
                st.caption(f"Environment: {self.config_manager.get_environment()}")
                st.caption(f"Debug mode: {self.config_manager.get_debug_mode()}")
        st.title("Rental Assistant Chatbot")

    def _add_logo(self):
        """Add logo at the top center of the page."""
        logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
        
        # Cache logo base64 string to avoid redundant file reads
        if self.logo_base64 is None:
            try:
                with open(logo_path, "rb") as f:
                    self.logo_base64 = base64.b64encode(f.read()).decode()
            except (FileNotFoundError, IOError):
                st.warning("⚠️ Logo file not found or unreadable. Please check the path to 'assets/logo.png'.")
                return

        st.markdown(
            f"""
            <style>
            .logo {{
                text-align: center;
            }}
            </style>
            <div class="logo">
                <img src="data:image/png;base64,{self.logo_base64}" width="200">
            </div>
            """,
            unsafe_allow_html=True
        )
    
    def _initialize_session_state(self):
        """Initialize chat message history in session state."""
        if "messages" not in st.session_state:
            st.session_state["messages"] = [
                {"role": "assistant", "content": "Hello 👋! Ask me anything about your rental agreements."}
            ]
    
    def _display_chat_history(self):
        """Display existing chat messages."""
        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])
    
    def _handle_user_input(self):
        """Handle user input and generate chatbot response."""
        if user_query := st.chat_input("Type your message..."):
            # Add user message
            st.session_state["messages"].append({"role": "user", "content": user_query})
            st.chat_message("user").write(user_query)
            
            # Get bot response
            response = self.chatbot.get_response(user_query)
            
            # Add assistant message
            st.session_state["messages"].append({"role": "assistant", "content": response})
            st.chat_message("assistant").write(response)
    
    def run(self):
        """Run the main application."""
        self._display_chat_history()
        self._handle_user_input()


# Initialize and run the application
if __name__ == "__main__":
    app = StreamlitApp()
    app.run()