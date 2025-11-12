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

from utils.current_auth import set_current_auth
from utils.moderation import moderate_content, get_moderation_message
import requests
from audiorecorder import audiorecorder
from utils.voice import VoiceManager

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
        self.voice_manager = VoiceManager(self.config_manager.api_key)
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
            [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4,
            [data-testid="stSidebar"] p,
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
                color: #000 !important;
                font-size: 0.9rem !important;
                padding: 0.4rem 0.6rem !important;
            }}
            div[data-testid="stExpander"] input:focus {{
                outline: none !important;
                border: 1px solid {self.RED} !important;
                box-shadow: 0 0 5px rgba(216,67,57,0.3) !important;
            }}
            
            /* Buttons */
            div[data-testid="stExpander"] .stButton > button {{
                border: none !important;
                background: {self.RED} !important;
                color: #fff !important;
                border-radius: 999px !important;
                font-weight: 600 !important;
                font-size: 0.9rem !important;
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

            /* Expander title styling */
            div[data-testid="stExpander"] > div:first-child p {{
                font-size: 1.1rem !important;
                font-weight: 700 !important;
                color: #FFFFFF !important;
                text-align: center !important;
            }}

            /* Voice section in sidebar */
            .voice-section {{
                padding: 0.8rem 0.5rem;
                margin: 0.5rem 0;
            }}
            
            .voice-hint {{
                color: rgba(255,255,255,0.9);
                font-size: 0.88rem;
                line-height: 1.5;
                margin-bottom: 0.7rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            
            /* Make all parent divs of the audio recorder transparent */
            div[data-testid="stAudio"],
            div[data-testid="stAudio"] > div,
            div[data-testid="stAudio"] > div > div,
            div[data-testid="stVerticalBlock"],
            div[data-testid="stVerticalBlock"] > div,
            div[data-testid="stVerticalBlock"] > div > div {{
                background: transparent !important;
                padding: 0 !important;
                margin: 0 !important;
                border: none !important;
                box-shadow: none !important;
            }}

            /* Also remove padding/margin from the column container */
            div[data-testid="column"] {{
                padding: 0 !important;
                margin: 0 !important;
            }}

            /* Remove any internal min-height / extra spacing */
            .stAudio, [data-testid="stAudio"] {{
                min-height: 0 !important;
            }}

            /* Keep buttons flush and without spacing */
            .stAudio button,
            [data-testid="stAudio"] button,
            div[data-testid="stVerticalBlock"] button[kind="secondary"] {{
                margin: 0 !important;
                padding: 0 !important;
                background: transparent !important;
                border: none !important;
                width: auto !important;
                height: auto !important;
                min-width: auto !important;
                min-height: auto !important;
            }}

            [data-testid="column"] > div {{
                gap: 0 !important;
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
        
        # Voice-specific state
        if "voice_enabled" not in st.session_state:
            st.session_state["voice_enabled"] = False
        
        if "tts_voice" not in st.session_state:
            st.session_state["tts_voice"] = "nova"
        
        if "pending_voice_query" not in st.session_state:
            st.session_state["pending_voice_query"] = None
        
        if "last_audio_bytes" not in st.session_state:
            st.session_state["last_audio_bytes"] = None

    def _api_base(self) -> str:
        """Determines the base API URL"""
        try:
            if "api" in st.secrets and "base_url" in st.secrets["api"]:
                return st.secrets["api"]["base_url"].rstrip("/")
        except Exception:
            pass
        return os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")

    def _api_login(self, email: str, password: str):
        API_BASE = self._api_base()
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
                auth_data = {
                    "token": token,
                    "user_id": str(user_id),
                    "email": data.get("email", email),
                    "logged_in": True,
                }
                
                st.session_state["auth"] = auth_data
                set_current_auth(auth_data)
                
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

    def _render_sidebar(self):
        with st.sidebar:
            # debug/config block
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
        
            # Login / Logout
            with st.expander("🔐 Login / Logout", expanded=False):
                email = st.text_input("Email", key="auth_email")
                pwd = st.text_input("Password", type="password", key="auth_pwd")

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Login", use_container_width=True, disabled=st.session_state["auth"]["logged_in"]):
                        self._api_login(email, pwd)
                with c2:
                    if st.button("Logout", use_container_width=True, disabled=not st.session_state["auth"]["logged_in"]):
                        self._api_logout()

                auth = st.session_state["auth"]
                if auth["logged_in"]:
                    st.success(f"Logged in as: {auth.get('email') or 'user'}")
                else:
                    st.caption("You're not logged in.")
            
            if st.session_state.get("auth", {}).get("logged_in"):
                st.caption(f"🔐 Auth persisted: {st.session_state['auth'].get('email')}")
                st.caption(f"User ID: {st.session_state['auth'].get('user_id')}")
            
            st.divider()

            # Voice Input Section - Simple and Clean
            st.markdown("<div class='voice-section'>", unsafe_allow_html=True)
            
            # Create a clean layout with text and button side by side
            col1, col2 = st.columns([3.25, 1])
            
            with col1:
                st.markdown(
                    "<p class='voice-hint'>Prefer to speak? Record your message instead of typing.</p>",
                    unsafe_allow_html=True
                )
            
            with col2:
                # Audio recorder with cleaner radio waves emoji (common in voice apps)
                audio_bytes = audiorecorder("🔴", "⏹️", key="sidebar_voice")
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Process voice input only if it's new audio
            if audio_bytes and len(audio_bytes) > 0:
                # Convert AudioSegment to bytes for hashing
                try:
                    # Export audio to bytes
                    from io import BytesIO
                    audio_buffer = BytesIO()
                    audio_bytes.export(audio_buffer, format="wav")
                    audio_data = audio_buffer.getvalue()
                    
                    # Check if this is new audio (different from last processed)
                    current_audio_hash = hash(audio_data)
                    last_audio_hash = st.session_state.get("last_audio_hash", None)
                    
                    if current_audio_hash != last_audio_hash:
                        st.session_state["last_audio_hash"] = current_audio_hash
                        
                        with st.spinner("Transcribing..."):
                            transcribed_text = self.voice_manager.transcribe_audio(audio_bytes)
                        
                        if transcribed_text:
                            # Store in session state to be processed in main area
                            st.session_state["pending_voice_query"] = transcribed_text
                            st.rerun()
                        else:
                            st.error("Could not transcribe. Please try again.")
                except Exception as e:
                    st.error(f"Error processing audio: {e}")
            
            st.divider()

            # Feedback/bug report
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

    def _display_chat_history(self):
        for msg in st.session_state["messages"]:
            role = msg["role"]
            content = msg["content"]
            avatar = self.user_icon if role == "user" else self.idle_icon
            bubble_class = "ca-user" if role == "user" else "ca-assist"

            with st.chat_message(role, avatar=avatar):
                st.markdown(f'<div class="ca-bubble {bubble_class}">{content}</div>', unsafe_allow_html=True)

    def _process_query(self, user_query: str):
        """Process a user query (from text or voice)"""
        print(f"[APP] Moderating user input: {user_query[:50]}...")
        moderation_result = moderate_content(user_query, self.config_manager.api_key)

        if not moderation_result["is_safe"]:
            flagged_cats = moderation_result["flagged_categories"]
            print(f"[APP] Content flagged: {flagged_cats}")

            warning_msg = get_moderation_message(flagged_cats)

            # Show user message
            st.session_state["messages"].append({"role": "user", "content": user_query})
            with st.chat_message("user", avatar=self.user_icon):
                st.markdown(f'<div class="ca-bubble ca-user">{user_query}</div>', unsafe_allow_html=True)

            # Show moderation warning
            warning_response = (
                f"⚠️ {warning_msg}\n\n"
                "Please rephrase your message to comply with our community guidelines. "
                "Casa Amigo is here to help with rental-related questions in a respectful manner."
            )

            with st.chat_message("assistant", avatar=self.idle_icon):
                st.markdown(f'<div class="ca-bubble ca-assist">{warning_response}</div>', unsafe_allow_html=True)

            st.session_state["messages"].append({"role": "assistant", "content": warning_response})

            if "moderation_flags" not in st.session_state:
                st.session_state["moderation_flags"] = []
            st.session_state["moderation_flags"].append({
                "timestamp": time.time(),
                "query": user_query,
                "categories": flagged_cats
            })

            return

        # Content is safe - Continue with normal flow
        print(f"[APP] Content passed moderation")

        # user message
        st.session_state["messages"].append({"role": "user", "content": user_query})
        with st.chat_message("user", avatar=self.user_icon):
            st.markdown(f'<div class="ca-bubble ca-user">{user_query}</div>', unsafe_allow_html=True)

        # assistant thinking + reply
        with st.chat_message("assistant", avatar=self.thinking_icon):
            placeholder = st.empty()
            for _ in range(3):
                dots_html = "<span class='ca-dot'></span>" * 3
                placeholder.markdown(f"<div class='ca-typing'>{dots_html}</div>", unsafe_allow_html=True)
                time.sleep(0.35)

            try:
                auth = st.session_state.get("auth", {})
                print(f"[APP] Auth state: user_id={auth.get('user_id')}, has_token={bool(auth.get('token'))}, logged_in={auth.get('logged_in')}")
                set_current_auth(auth)
                response = self.chatbot.chat(user_query, auth=auth)

                # Moderate assistant response
                print(f"[APP] Moderating assistant response")
                response_mod = moderate_content(response, self.config_manager.api_key)

                if not response_mod["is_safe"]:
                    print(f"[APP] WARNING: Assistant response was flagged: {response_mod['flagged_categories']}")
                    response = (
                        "I apologize, but I need to rephrase my response. "
                        "Let me try again with a different approach."
                    )

            except Exception as e:
                response = "⚠️ Sorry, something went wrong. Please try again."
                st.toast(f"Backend error: {e}")

            placeholder.markdown(f"<div class='ca-bubble ca-assist'>{response}</div>", unsafe_allow_html=True)
            
            # Voice responses are removed - keeping interface clean and simple

            # debug expander
            if self.config_manager.get_debug_mode():
                with st.sidebar.expander("🔎 Debug (last turn)", expanded=False):
                    st.write("**Input Moderation:**")
                    if moderation_result.get("error"):
                        st.warning(f"Moderation error: {moderation_result['error']}")
                    else:
                        st.write(f"✅ Safe: {moderation_result['is_safe']}")
                        if moderation_result['flagged_categories']:
                            st.write(f"⚠️ Flagged: {', '.join(moderation_result['flagged_categories'])}")
                    
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

    def _handle_user_input(self):
        # Check for pending voice query from sidebar
        if st.session_state.get("pending_voice_query"):
            query = st.session_state["pending_voice_query"]
            st.session_state["pending_voice_query"] = None  # Clear it
            self._process_query(query)
            st.rerun()
            return
        
        # Handle text input
        if user_query := st.chat_input("Type your message..."):
            self._process_query(user_query)
            st.rerun()

        # footer below chat box
        st.markdown(
            "<div class='ca-main-footer'>⚡ Powered by <b>Casa Amigo</b> © 2025 — Simplifying rentals, one chat at a time.</div>",
            unsafe_allow_html=True,
        )

    def run(self):
        self._render_sidebar()
        self._display_chat_history()
        self._handle_user_input()


if __name__ == "__main__":
    load_dotenv()
    app = StreamlitApp()
    app.run()