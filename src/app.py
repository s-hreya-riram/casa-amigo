# src/app.py
import os
import time
import streamlit as st
from dotenv import load_dotenv
from services.factory import auth_service
from core.config.jwt_handler import create_access_token
from utils.tool_registry import consume_debug_log
from config import ConfigManager
from core import DocumentIndexManager, CasaAmigoAgent

class StreamlitApp:

    RED = "#D84339"
    BLUE = "#2C4B8E"
    NAVY = "#07090D"
    idle_icon = os.path.join(os.path.dirname(__file__), "..", "assets", "blink_robot_avatar.gif")
    thinking_icon = os.path.join(os.path.dirname(__file__), "..", "assets", "load_robot_avatar.gif")
    user_icon = os.path.join(os.path.dirname(__file__), "..", "assets", "user_avatar.png")

    def __init__(self):
        self.config_manager = ConfigManager()
        self.doc_manager = DocumentIndexManager()
        self.chatbot = CasaAmigoAgent(self.doc_manager.index, self.config_manager.api_key)
        self._setup_page()
        self._inject_styles()
        self._initialize_session_state()

    def _setup_page(self):
        st.set_page_config(page_title="Casa Amigo Chatbot", page_icon="🏠", layout="wide")
        st.markdown(
            f"<div style='display:flex;justify-content:center;align-items:center;gap:10px;font-weight:800;font-size:2rem;color:{self.BLUE};'>"
            "Your Rental Assistant Chatbot</div>",
            unsafe_allow_html=True
        )

    def _inject_styles(self):
        # (keep your existing CSS styles here)
        pass

    def _initialize_session_state(self):
        if "messages" not in st.session_state:
            st.session_state["messages"] = [
                {"role": "assistant", "content": "Hello!👋 Ask me anything about your rental agreements."}
            ]
        if "bug_reports" not in st.session_state:
            st.session_state["bug_reports"] = []
        if "auth" not in st.session_state:
            st.session_state["auth"] = {
                "token": None,
                "user_id": None,
                "email": None,
                "logged_in": False,
            }

    # ===== AUTH HELPERS =====
    def login(self, email: str, password: str):
        email = (email or "").strip()
        password = (password or "").strip()
        if not email or not password:
            st.error("Email and password are required.")
            return False
        try:
            user = auth_service.login(email, password)
            token = create_access_token(user_id=user.get("user_id"))
            st.session_state["auth"] = {
                "token": token,
                "user_id": user.get("user_id"),
                "email": user.get("email_id"),
                "logged_in": True
            }
            st.toast("Logged in.")
            return True
        except Exception as e:
            st.error(f"Login failed: {e}")
            return False

    def logout(self):
        st.session_state["auth"] = {
            "token": None,
            "user_id": None,
            "email": None,
            "logged_in": False,
        }
        st.toast("Logged out.")

    # ===== SIDEBAR =====
    def _render_sidebar(self):
        with st.sidebar:
            # Debug / config
            if self.config_manager.get_debug_mode():
                st.subheader("🔧 Configuration Status")
                if st.button("🔁 Rebuild index (parse clauses)"):
                    self.doc_manager.rebuild()
                    st.success("Index rebuilt.")
                st.caption(f"Environment: {self.config_manager.get_environment()}")
                st.caption(f"Debug mode: {self.config_manager.get_debug_mode()}")
                st.divider()

            # Logo
            logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
            if os.path.exists(logo_path):
                st.image(logo_path, use_container_width=True)

            # Login / Logout
            with st.expander("🔐 Login / Logout", expanded=False):
                email = st.text_input("Email", key="auth_email")
                pwd = st.text_input("Password", type="password", key="auth_pwd")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Login", use_container_width=True):
                        self.login(email, pwd)
                with c2:
                    if st.button("Logout", use_container_width=True, disabled=not st.session_state["auth"]["logged_in"]):
                        self.logout()
                auth = st.session_state["auth"]
                if auth["logged_in"]:
                    st.success(f"Logged in as: {auth.get('email')}")
                else:
                    st.caption("You’re not logged in.")

            st.divider()
            # Bug report
            st.markdown("<h3 style='text-align:center;'>🐞 Feedback/Bug Report</h3>", unsafe_allow_html=True)
            with st.form("bugform", clear_on_submit=True):
                bug = st.text_area("Tell us what went wrong.", height=100)
                submitted = st.form_submit_button("Submit")
                if submitted and bug.strip():
                    st.session_state["bug_reports"].append(bug.strip())
                    st.success("Thanks for sharing!")

    # ===== CHAT =====
    def _display_chat_history(self):
        for msg in st.session_state["messages"]:
            role = msg["role"]
            content = msg["content"]
            avatar = self.user_icon if role == "user" else self.idle_icon
            bubble_class = "ca-user" if role == "user" else "ca-assist"
            with st.chat_message(role, avatar=avatar):
                st.markdown(f'<div class="ca-bubble {bubble_class}">{content}</div>', unsafe_allow_html=True)

    def _handle_user_input(self):
        if user_query := st.chat_input("Type your message..."):
            st.session_state["messages"].append({"role": "user", "content": user_query})
            with st.chat_message("user", avatar=self.user_icon):
                st.markdown(f'<div class="ca-bubble ca-user">{user_query}</div>', unsafe_allow_html=True)

            with st.chat_message("assistant", avatar=self.thinking_icon):
                placeholder = st.empty()
                for _ in range(3):
                    placeholder.markdown("<div class='ca-typing'><span class='ca-dot'></span>"*3 + "</div>", unsafe_allow_html=True)
                    time.sleep(0.35)
                try:
                    response = self.chatbot.chat(user_query)
                except Exception:
                    response = "⚠️ Something went wrong."
                placeholder.markdown(f"<div class='ca-bubble ca-assist'>{response}</div>", unsafe_allow_html=True)
                st.session_state["messages"].append({"role": "assistant", "content": response})

    # ===== RUN APP =====
    def run(self):
        self._render_sidebar()
        tenant_tab, agent_tab = st.tabs(["👤 Tenant", "🧑‍💼 Agent"])
        with tenant_tab:
            self._display_chat_history()
            self._handle_user_input()
        with agent_tab:
            st.subheader("Agent (preview)")
            st.caption("Read-only placeholder.")

if __name__ == "__main__":
    load_dotenv()
    app = StreamlitApp()
    app.run()
