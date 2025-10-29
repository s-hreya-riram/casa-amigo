# src/app.py
import os
import time
import base64
import streamlit as st
from dotenv import load_dotenv
from typing import List, Dict, Any
from utils.tool_registry import consume_debug_log
from config import ConfigManager
from core import DocumentIndexManager, CasaAmigoAgent
import requests

class StreamlitApp:

    # brand palette & asset paths
    RED: str = "#D84339"
    BLUE: str = "#2C4B8E"
    NAVY: str = "#07090D"
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

    # page chrome
    def _setup_page(self):
        st.set_page_config(page_title="Casa Amigo Chatbot", page_icon="🏠", layout="wide")
        st.markdown(
            f"""
            <div style="
                display:flex;justify-content:center;align-items:center;
                gap:10px;flex-wrap:wrap;margin:0 0 14px 0;
                font-weight:800;font-size:2rem;line-height:1.2;color:{self.BLUE};
            ">
              <span style="font-size:2.1rem;"> Your Rental Assistant Chatbot</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def _inject_styles(self):
        """styling (gradient sidebar, bubbles, avatars, footer, red focus)"""
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
              [data-testid="stSidebar"] label {{ color: #FFFFFF !important; }}
              [data-testid="stSidebar"] hr {{
                border: none; border-top: 1px solid rgba(255,255,255,0.3);
                margin: .6rem 0 1rem 0;
              }}
              .ca-tagline {{
                text-align: center; font-style: italic; color: #FFFFFF;
                opacity: 0.95; margin-top: -6px; margin-bottom: 12px;
              }}

              /* Red focus */
              [data-testid="stSidebar"] textarea,
              [data-testid="stChatInput"] textarea {{
                background: #FFFFFF !important; color: #000 !important;
                border: 2px solid {self.RED}80 !important; border-radius: 10px !important;
                font-size: 1rem !important; padding: 0.6rem 1rem !important;
                outline: none !important; box-shadow: none !important;
                transition: border 0.15s ease-in-out;
              }}
              [data-testid="stSidebar"] textarea:focus,
              [data-testid="stChatInput"] textarea:focus {{
                border: 2px solid {self.RED} !important;
                box-shadow: 0 0 6px {self.RED}60 !important;
              }}

              /* Buttons (pill) */
              .stButton>button {{
                border: 2px solid {self.RED}; color: {self.RED};
                background: transparent; border-radius: 999px;
                padding: .55rem 1rem; font-weight: 600;
                transition: all 0.2s ease-in-out;
              }}
              .stButton>button:hover {{ background: {self.RED} !important; color: #FFF !important; }}

              /* Chat bubbles */
              .ca-bubble {{
                border-radius: 18px; padding: 14px 16px; margin: 6px 0;
                color: #0A0A0A; backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
              }}
              .ca-user {{ background: rgba(216, 67, 57, 0.08); border-left: 4px solid {self.RED}; }}
              .ca-assist {{ background: rgba(44, 75, 142, 0.08); border-left: 4px solid {self.BLUE}; }}

              /* Avatars larger & circular */
              [data-testid="stChatMessage"] img {{
                border-radius: 50% !important; border: 3px solid #fff;
                width: 70px !important; height: 70px !important; object-fit: cover;
              }}

              /* Typing indicator */
              .ca-typing {{
                display:inline-block; border-radius: 18px; padding: 12px 16px; margin: 6px 0;
                background: rgba(44, 75, 142, 0.08); border-left: 4px solid {self.BLUE};
              }}
              .ca-dot {{
                display:inline-block; width:6px; height:6px; margin:0 2px;
                background:{self.BLUE}; border-radius:50%; animation: ca-bounce 1s infinite;
              }}
              .ca-dot:nth-child(2) {{ animation-delay: .15s; }}
              .ca-dot:nth-child(3) {{ animation-delay: .3s; }}
              @keyframes ca-bounce {{
                0%, 80%, 100% {{ transform: scale(1); opacity:.6; }}
                40% {{ transform: scale(1.6); opacity:1; }}
              }}

              .ca-footer {{ text-align:center; font-size:.85rem; color:rgba(255,255,255,0.8); margin-top:10px; }}
              .ca-main-footer {{ text-align:center; font-size:.85rem; color:#666; margin-top:14px; opacity:.8; }}

                /* Sidebar Login Section Styling */
              div[data-testid="stExpander"] {{
                border-radius: 14px !important;
                background: rgba(255,255,255,0.1) !important;
                border: 1px solid rgba(255,255,255,0.25) !important;
                color: #fff !important;
              }}

              /* Inputs: light box + black text */
              div[data-testid="stExpander"] input {{
                background: #fff !important;
                border: 1px solid rgba(255,255,255,0.6) !important;
                border-radius: 8px !important;
                color: #000 !important;               /* black text */
                font-size: 0.9rem !important;
                padding: 0.4rem 0.6rem !important;
              }}
              div[data-testid="stExpander"] input:focus {{
                outline: none !important;
                border: 1px solid {self.RED} !important; /* Casa Amigo red */
                box-shadow: 0 0 5px rgba(216,67,57,0.3) !important;
              }}

              /* Buttons */
              div[data-testid="stExpander"] .stButton > button {{
                border: none !important;
                background: {self.RED} !important;
                color: #fff !important;
                border-radius: 999px !important;
                font-weight: 600 !important;
                font-size: 0.9rem !important;        /* smaller font */
                padding: 0.45rem 1.1rem !important;
                width: 100%;
                transition: all 0.2s ease-in-out;
              }}
              div[data-testid="stExpander"] .stButton > button:hover {{
                background: #b7352d !important;
                color: #fff !important;
                transform: translateY(-1px);
              }}

              /* Status + label colors */
              div[data-testid="stExpander"] label,
              div[data-testid="stExpander"] p,
              div[data-testid="stExpander"] .stCaption,
              div[data-testid="stExpander"] .stInfo {{
                color: rgba(255,255,255,0.9) !important;
                font-size: 0.9rem !important;
              }}

                /* Expander title (🔐 Login / Logout) styling */
              div[data-testid="stExpander"] > div:first-child p {{
                font-size: 1.1rem !important;       /* same as Feedback title */
                font-weight: 700 !important;        /* bold */
                color: #FFFFFF !important;          /* white text */
                text-align: center !important;
              }}

            </style>
            """,
            unsafe_allow_html=True,
        )

    # state
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

        # ========== AUTH HELPERS (LOCAL API) ==========
    def _api_base(self) -> str:
        # Use env var if present; default to local FastAPI
        return os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")

    def _api_available(self) -> bool:
        try:
            r = requests.get(f"{self._api_base()}/health", timeout=2)
            return r.ok
        except Exception:
            return False

    def _api_login(self, email: str, password: str):

        API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")

        email = (email or "").strip()
        password = (password or "").strip()
        if not email or not password:
            st.error("Email and password are required.")
            return False

        try:
            r = requests.post(
                f"{API_BASE}/auth/login",
                params={"email": email, "password": password},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()

            token = data.get("access_token") or data.get("token")
            user_id = data.get("user_id")
            if token:
                st.session_state["auth"] = {
                    "token": token,
                    "user_id": user_id,
                    "email": data.get("email", email),
                    "logged_in": True,
                }
                st.toast("Logged in.")
                return True

            st.error("Login response missing token.")
        except requests.HTTPError as e:
            try:
                detail = r.json().get("detail")
            except Exception:
                detail = str(e)
            st.error(f"Login failed: {detail}")
        except Exception as e:
            st.error(f"Login failed: {e}")
        return False

    def _api_logout(self):
        st.session_state["auth"] = {
            "token": None,
            "user_id": None,
            "email": None,
            "logged_in": False,
        }
        st.toast("Logged out.")

    # sidebar
    def _render_sidebar(self):
        with st.sidebar:
            # debug/config block (only when debug mode ON)
            if self.config_manager.get_debug_mode():
                st.subheader("🔧 Configuration Status")

                if st.button("🔁 Rebuild index (parse clauses)"):
                    self.doc_manager.rebuild()
                    st.success("Index rebuilt with clause metadata.")

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
                st.divider()

            # sidebar visuals
            logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
            if os.path.exists(logo_path):
                st.image(logo_path, use_container_width=True)
            else:
                st.warning("⚠️ Logo not found at the specified path.")

            st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)
            st.markdown(
                "<h3 style='text-align:center; color:white; font-weight:700; margin-bottom:2px'> Your Rental Assistant Chatbot</h3>",
                unsafe_allow_html=True,
            )
            st.markdown("<div class='ca-tagline'>Simplifying rentals, <br>one chat at a time.</div>", unsafe_allow_html=True)
            st.divider()
        
            #  Login / Logout
            api_up = self._api_available()
            with st.expander("🔐 Login / Logout", expanded=False):
                if not api_up:
                    st.info("Local API not detected at 127.0.0.1:8000 — login is disabled until the backend is running.")

                email = st.text_input("Email", key="auth_email")
                pwd   = st.text_input("Password", type="password", key="auth_pwd")

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Login", use_container_width=True, disabled=not api_up):
                        self._api_login(email, pwd)
                with c2:
                    if st.button("Logout", use_container_width=True, disabled=not st.session_state["auth"]["logged_in"]):
                        self._api_logout()

                auth = st.session_state["auth"]
                if auth["logged_in"]:
                    st.success(f"Logged in as: {auth.get('email') or 'user'}")
                else:
                    st.caption("You’re not logged in.")
            
            st.divider()

            # feedback/bug report

            st.markdown("<h3 style='text-align:center;'>🐞 Feedback/Bug Report</h3>", unsafe_allow_html=True)
            with st.form("bugform", clear_on_submit=True):
                bug = st.text_area("Tell us what went wrong or how we can improve.", height=100)
                submitted = st.form_submit_button("Submit")
                if submitted and bug.strip():
                    st.session_state["bug_reports"].append(bug.strip())
                    st.success("Thanks for sharing! We truly appreciate your feedback.")

            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            st.divider()

            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state["messages"] = [
                    {"role": "assistant", "content": "Hello!👋 Ask me anything about your rental agreements."}
                ]
                st.toast("Chat history cleared.")

            st.markdown("<div class='ca-footer'>⚡ Powered by Casa Amigo © 2025</div>", unsafe_allow_html=True)

    # chat handling
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
            # user message
            st.session_state["messages"].append({"role": "user", "content": user_query})
            with st.chat_message("user", avatar=self.user_icon):
                st.markdown(f'<div class="ca-bubble ca-user">{user_query}</div>', unsafe_allow_html=True)

            # assistant thinking + reply via CasaAmigoAgent.chat()
            with st.chat_message("assistant", avatar=self.thinking_icon):
                placeholder = st.empty()
                for _ in range(3):
                    dots_html = "<span class='ca-dot'></span>" * 3
                    placeholder.markdown(f"<div class='ca-typing'>{dots_html}</div>", unsafe_allow_html=True)
                    time.sleep(0.35)

                try:
                    response = self.chatbot.chat(user_query)
                except Exception as e:
                    response = "⚠️ Sorry, something went wrong. Please try again."
                    st.toast(f"Backend error: {e}")

                placeholder.markdown(f"<div class='ca-bubble ca-assist'>{response}</div>", unsafe_allow_html=True)

                # debug expander (per-turn)
                with st.sidebar.expander("🔎 Debug (last turn)", expanded=True):
                    # Tool registry logs
                    logs = consume_debug_log()
                    if not logs:
                        st.caption("No tool logs yet.")
                    else:
                        for row in logs:
                            if row["event"] == "tool_called":
                                st.write(f"**Tool:** `{row['tool']}`")
                                st.code(row["args"])
                            elif row["event"] == "retrieval":
                                st.write(f"**retrieved_k:** {row['retrieved_k']}")
                                top = row.get("top", [])
                                if top:
                                    st.write("**Top-3:**")
                                    for t in top:
                                        st.write(f"- #{t['rank']} — score={t['score']} — {t['label']}")
                            elif row["event"] == "tool_error":
                                st.error(f"{row['tool']} error: {row['error']}")

                    # agent tool calls (if available)
                    calls = self.chatbot.get_tool_calls() if hasattr(self.chatbot, "get_tool_calls") else []
                    if calls:
                        st.markdown("---")
                        st.write("**Agent tool calls**")
                        for c in calls:
                            st.write(f"- #{c['i']} **{c['name']}**")
                            st.code(c["args"])
                    else:
                        st.caption("No agent tool calls recorded.")

            # persist assistant message
            st.session_state["messages"].append({"role": "assistant", "content": response})

        # footer below chat box
        st.markdown(
            "<div class='ca-main-footer'>⚡ Powered by <b>Casa Amigo</b> © 2025 — Simplifying rentals, one chat at a time.</div>",
            unsafe_allow_html=True,
        )

    # main run
    def run(self):
        self._render_sidebar()

        # tabs: Tenant (chat) | Agent (placeholder) 
        tenant_tab, agent_tab = st.tabs(["👤 Tenant", "🧑‍💼 Agent"])

        with tenant_tab:
            self._display_chat_history()
            self._handle_user_input()

        with agent_tab:
            st.subheader("Agent (preview)")
            st.caption("This is a read-only placeholder.")
            st.markdown(
                "- (coming soon)\n"
                "- (coming soon)\n"
                "- (coming soon)"
            )
        

if __name__ == "__main__":
    load_dotenv()
    app = StreamlitApp()
    app.run()