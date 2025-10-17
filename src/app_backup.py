import os
import time
import streamlit as st
from typing import List, Dict, Any

from config import ConfigManager
from core import ChatbotEngine, DocumentIndexManager


class StreamlitApp:
    """Manages the Streamlit UI and user interactions."""

    RED: str = "#D84339"
    BLUE: str = "#2C4B8E"
    NAVY: str = "#1F2A60"

    def __init__(self):
        self.config_manager = ConfigManager()
        self.doc_manager = DocumentIndexManager()
        self.chatbot = ChatbotEngine(self.doc_manager.index, self.config_manager.api_key)
        self._setup_page()
        self._inject_styles()
        self._initialize_session_state()

    def _setup_page(self):
        st.set_page_config(page_title="Casa Amigo Chatbot", page_icon="🏠", layout="wide")
        st.markdown(
            f"""
            <div style="
                display:flex;justify-content:center;align-items:center;
                gap:10px;flex-wrap:wrap;margin:0 0 14px 0;
                font-weight:800;font-size:2rem;line-height:1.2;color:{self.BLUE};
            ">
              <span style="font-size:2.1rem;">🏠</span>
              <span>Casa Amigo – Rental Assistant Chatbot</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def _inject_styles(self):
        """Inject Casa Amigo styles with red-only focus and footer."""
        st.markdown(
            f"""
            <style>
              .block-container {{
                padding-top: 1.1rem;
                padding-bottom: 2rem;
                background: #FFFFFF;
              }}

              /* Sidebar gradient */
              [data-testid="stSidebar"] > div:first-child {{
                background: linear-gradient(180deg, {self.NAVY} 0%, {self.BLUE} 55%, {self.RED} 130%);
                color: #FFFFFF;
              }}

              [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
              [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p,
              [data-testid="stSidebar"] label {{
                color: #FFFFFF !important;
              }}
              [data-testid="stSidebar"] hr {{
                border: none;
                border-top: 1px solid rgba(255,255,255,0.3);
                margin: .6rem 0 1rem 0;
              }}

              .ca-tagline {{
                text-align: center;
                font-style: italic;
                color: #FFFFFF;
                opacity: 0.95;
                margin-top: -6px;
                margin-bottom: 12px;
              }}

              /* Red-only focus for feedback + chat input */
              [data-testid="stSidebar"] textarea,
              [data-testid="stChatInput"] textarea {{
                background: #FFFFFF !important;
                color: #000000 !important;
                border: 2px solid {self.RED}80 !important;
                border-radius: 10px !important;
                font-size: 1rem !important;
                padding: 0.6rem 1rem !important;
                outline: none !important;
                box-shadow: none !important;
                transition: border 0.15s ease-in-out;
              }}
              [data-testid="stSidebar"] textarea:focus,
              [data-testid="stChatInput"] textarea:focus {{
                border: 2px solid {self.RED} !important;
                box-shadow: 0 0 6px {self.RED}60 !important;
                outline: none !important;
              }}

              /* Submit button – navy pill */
              [data-testid="stSidebar"] .stFormSubmitButton>button {{
                border: 2px solid {self.NAVY};
                color: {self.NAVY};
                background: transparent;
                border-radius: 999px;
                padding: .55rem 1rem;
                font-weight: 600;
                transition: all 0.2s ease-in-out;
              }}
              [data-testid="stSidebar"] .stFormSubmitButton>button:hover {{
                background: {self.NAVY} !important;
                color: #FFFFFF !important;
              }}

              /* Clear Chat button – red pill */
              .stButton>button {{
                border: 2px solid {self.RED};
                color: {self.RED};
                background: transparent;
                border-radius: 999px;
                padding: .55rem 1rem;
                font-weight: 600;
                transition: all 0.2s ease-in-out;
              }}
              .stButton>button:hover {{
                background: {self.RED} !important;
                color: #FFF !important;
              }}

              /* Glass chat bubbles */
              .ca-bubble {{
                border-radius: 18px;
                padding: 14px 16px;
                margin: 6px 0;
                color: #0A0A0A;
                backdrop-filter: blur(6px);
                -webkit-backdrop-filter: blur(6px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
              }}
              .ca-user {{
                background: rgba(216, 67, 57, 0.08);
                border-left: 4px solid {self.RED};
              }}
              .ca-assist {{
                background: rgba(44, 75, 142, 0.08);
                border-left: 4px solid {self.BLUE};
              }}

              /* Circular avatars */
              [data-testid="stChatMessageAvatar"] img {{
                border-radius: 50% !important;
                border: 3px solid #fff;
              }}

              /* Typing indicator */
              .ca-typing {{
                display:inline-block;
                border-radius: 18px;
                padding: 12px 16px;
                margin: 6px 0;
                background: rgba(44, 75, 142, 0.08);
                border-left: 4px solid {self.BLUE};
              }}
              .ca-dot {{
                display:inline-block; width:6px; height:6px; margin:0 2px;
                background:{self.BLUE}; border-radius:50%;
                animation: ca-bounce 1s infinite;
              }}
              .ca-dot:nth-child(2) {{ animation-delay: .15s; }}
              .ca-dot:nth-child(3) {{ animation-delay: .3s; }}
              @keyframes ca-bounce {{
                0%, 80%, 100% {{ transform: scale(1); opacity:.6; }}
                40% {{ transform: scale(1.6); opacity:1; }}
              }}

              /* Footer styles */
              .ca-footer {{
                text-align: center;
                font-size: 0.85rem;
                color: rgba(255,255,255,0.8);
                margin-top: 10px;
              }}
              .ca-main-footer {{
                text-align:center;
                font-size:0.85rem;
                color:#666;
                margin-top:14px;
                opacity:0.8;
              }}
            </style>
            """,
            unsafe_allow_html=True,
        )

    def _initialize_session_state(self):
        if "messages" not in st.session_state:
            st.session_state["messages"] = [
                {"role": "assistant", "content": "Hello!👋 Ask me anything about your rental agreements."}
            ]
        if "bug_reports" not in st.session_state:
            st.session_state["bug_reports"] = []

    def _render_sidebar(self):
        with st.sidebar:
            logo_path = os.path.join(
                "C:\\Users\\Awandhana\\Downloads\\M.Sc\\DSS5105 - Data Science Projects in Practice\\casa-amigo-main",
                "CALogo.png",
            )
            if os.path.exists(logo_path):
                st.image(logo_path, use_container_width=True)
            else:
                st.warning("⚠️ Logo not found at the specified path.")

            st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)
            st.markdown(
                "<h3 style='text-align:center; color:white; font-weight:700; margin-bottom:2px;'>🏠 Casa Amigo – Rental Assistant Chatbot</h3>",
                unsafe_allow_html=True,
            )
            st.markdown("<div class='ca-tagline'>Simplifying rentals, one chat at a time.</div>", unsafe_allow_html=True)
            st.divider()

            st.markdown("<h3 style='text-align:center;'>🐞 Feedback/Bug Report</h3>", unsafe_allow_html=True)
            with st.form("bugform", clear_on_submit=True):
                bug = st.text_area("Tell us what went wrong or how we can improve.", height=100)
                submitted = st.form_submit_button("Submit")
                if submitted and bug.strip():
                    st.session_state["bug_reports"].append(bug.strip())
                    st.success("✅ Thanks for sharing. We truly appreciate your feedback!")

            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            st.divider()

            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state["messages"] = [
                    {"role": "assistant", "content": "Hello!👋 Ask me anything about your rental agreements."}
                ]
                st.toast("Chat history cleared.")

            st.markdown("<div class='ca-footer'>⚡ Powered by Casa Amigo © 2025</div>", unsafe_allow_html=True)

    def _display_chat_history(self):
        for msg in st.session_state["messages"]:
            role = msg["role"]
            content = msg["content"]
            avatar = "🧑‍💼" if role == "user" else "🤖"
            bubble_class = "ca-user" if role == "user" else "ca-assist"

            with st.chat_message(role, avatar=avatar):
                st.markdown(f'<div class="ca-bubble {bubble_class}">{content}</div>', unsafe_allow_html=True)

    def _handle_user_input(self):
        if user_query := st.chat_input("Type your message..."):
            st.session_state["messages"].append({"role": "user", "content": user_query})
            with st.chat_message("user", avatar="🧑‍💼"):
                st.markdown(f'<div class="ca-bubble ca-user">{user_query}</div>', unsafe_allow_html=True)

            with st.chat_message("assistant", avatar="🤖"):
                placeholder = st.empty()
                for _ in range(3):
                    dots_html = "<span class='ca-dot'></span>" * 3
                    placeholder.markdown(f"<div class='ca-typing'>{dots_html}</div>", unsafe_allow_html=True)
                    time.sleep(0.35)
                response = self.chatbot.get_response(user_query)
                placeholder.markdown(f"<div class='ca-bubble ca-assist'>{response}</div>", unsafe_allow_html=True)

            st.session_state["messages"].append({"role": "assistant", "content": response})

        # Footer below chat box
        st.markdown(
            "<div class='ca-main-footer'>⚡ Powered by <b>Casa Amigo</b> © 2025 — Simplifying rentals, one chat at a time.</div>",
            unsafe_allow_html=True,
        )

    def run(self):
        self._render_sidebar()
        self._display_chat_history()
        self._handle_user_input()


if __name__ == "__main__":
    app = StreamlitApp()
    app.run()
