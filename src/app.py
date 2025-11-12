# src/app.py
import os
import time
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta
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
    # ===== BRAND COLORS & ASSETS =====
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

    # ===== SETUP & STYLING =====
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
        """Styling (gradient sidebar, bubbles, avatars, footer, typography)"""
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

            /* Motto */
            .ca-tagline-strong {{
                text-align: center;
                font-style: italic;
                color: #FFFFFF;
                opacity: 0.95;
                margin: .35rem 0 .6rem 0;
                line-height: 1.35;
                font-weight: 600;
            }}

            /* Red focus for textareas and chat input */
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

            /* --- Consistent typography --- */
            html, body, [class^="css"] {{
                font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
            }}
            [data-testid="stSidebar"] h3,
            [data-testid="stSidebar"] label {{ color: #ffffff !important; }}

            /* Tighten spacing */
            [data-testid="stSidebar"] h3 {{ margin: 0.35rem 0 0.5rem 0 !important; }}
            [data-testid="stSidebar"] label {{ font-weight: 600 !important; opacity: 0.95; }}

            /* Selectbox look */
            [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {{
                border-radius: 12px !important;
            }}
            [data-testid="stSidebar"] .stSelectbox {{
                margin-top: 0.4rem !important;
                margin-bottom: 0.6rem !important;
            }}

            /* Subtle separators */
            [data-testid="stSidebar"] .ca-sep {{
                border-top: 1px solid rgba(255,255,255,0.25);
                margin: 0.9rem 0 0.9rem 0;
            }}

            /* ---- IMPORTANT: do NOT fix-position the chat input ---- */
            /* (No [data-testid="stChatInputContainer"] position: fixed here) */
            </style>
            """,
            unsafe_allow_html=True,
        )

    # ===== SESSION STATE INITIALIZATION =====
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

    # ===== BACKEND AUTH HELPERS =====
    def _api_base(self) -> str:
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

    # ===== BACKEND DATA FETCHING =====
    def _auth_headers(self):
        token = st.session_state.get("auth", {}).get("token")
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _get_json(self, path: str, params: dict | None = None, fallback=None):
        base = self._api_base()
        try:
            r = requests.get(f"{base}{path}", params=params or {}, headers=self._auth_headers(), timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            st.caption(f"⚠️ Backend GET failed: {path} — {e}")
            return fallback

    def _fetch_properties(self, limit: int = 50, offset: int = 0) -> list[dict]:
        data = self._get_json("/properties", params={"limit": limit, "offset": offset}, fallback={"properties": []})
        return data.get("properties", [])

    # ===== PROPERTY SCORING =====
    def _score_properties(self, props: list[dict], prefs: dict | None) -> pd.DataFrame:
        if not props:
            return pd.DataFrame(columns=["property_id","title","price","beds","area","score","price_fit","beds_fit","area_fit","mrt_fit"])

        prefs = prefs or {}
        budget_max = prefs.get("budget_max") or prefs.get("max_budget")
        budget_min = prefs.get("budget_min") or prefs.get("min_budget")
        pref_beds  = prefs.get("min_bedrooms") or prefs.get("bedrooms")
        pref_areas = set([a.strip().lower() for a in (prefs.get("preferred_areas") or prefs.get("areas") or [])]) if isinstance(prefs.get("preferred_areas") or prefs.get("areas"), list) else set()

        rows = []
        for p in props:
            pid   = p.get("id") or p.get("property_id") or p.get("uuid") or "-"
            title = p.get("title") or p.get("name") or p.get("address") or "Listing"
            price = p.get("price") or p.get("monthly_rent") or p.get("rent") or None
            beds  = p.get("bedrooms") or p.get("beds") or None
            area  = (p.get("area") or p.get("district") or p.get("neighborhood") or "").strip()
            mrt   = p.get("mrt_distance_mins") or p.get("distance_mrt")

            price_fit = 0.5
            if price is not None:
                ok_min = (budget_min is None) or (price >= budget_min)
                ok_max = (budget_max is None) or (price <= budget_max)
                if ok_min and ok_max: price_fit = 1.0
                elif ok_min or ok_max: price_fit = 0.7
                else: price_fit = 0.2

            beds_fit = 0.5
            if pref_beds is not None and beds is not None:
                if int(beds) >= int(pref_beds): beds_fit = 1.0
                elif int(beds) == int(pref_beds) - 1: beds_fit = 0.7
                else: beds_fit = 0.2

            area_fit = 0.5
            if pref_areas:
                area_fit = 1.0 if area.lower() in pref_areas else 0.4

            mrt_fit = 0.5
            pref_walk = prefs.get("max_mrt_walk_mins")
            if mrt is not None:
                try:
                    mrt = float(mrt)
                    if pref_walk is not None:
                        mrt_fit = 1.0 if mrt <= float(pref_walk) else max(0.2, 1.0 - (mrt - float(pref_walk)) * 0.05)
                    else:
                        mrt_fit = 1.0 if mrt <= 10 else (0.7 if mrt <= 15 else 0.4)
                except Exception:
                    mrt_fit = 0.5

            score = round(0.4*price_fit + 0.25*beds_fit + 0.2*area_fit + 0.15*mrt_fit, 3)
            rows.append({
                "property_id": pid,
                "title": title,
                "price": price,
                "beds": beds,
                "area": area,
                "score": score,
                "price_fit": price_fit,
                "beds_fit": beds_fit,
                "area_fit": area_fit,
                "mrt_fit": mrt_fit,
            })

        df = pd.DataFrame(rows).sort_values(["score","price"], ascending=[False, True])
        return df

    # ===== SIDEBAR RENDERING =====
    def _render_sidebar(self):
        role = st.session_state.get("active_role")
        with st.sidebar:
            # 1) Logo
            logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
            if os.path.exists(logo_path):
                st.image(logo_path, use_container_width=True)
            else:
                st.warning("⚠️ Logo not found at the specified path.")

            # 2) Motto
            st.markdown(
                "<div class='ca-tagline-strong'>Simplifying rentals,<br>one chat at a time.</div>",
                unsafe_allow_html=True,
            )

            st.markdown("<div class='ca-sep'></div>", unsafe_allow_html=True)

            # 3) Navigation Header
            st.markdown("<h3>🧭 Navigation</h3>", unsafe_allow_html=True)
            tenant_menu = ["Conversations", "Profile", "Logout"]
            agent_menu  = ["Dashboard", "Profile", "Logout"]
            menu = tenant_menu if role == "tenant" else agent_menu

            prev = st.session_state.get("sidebar_nav")
            default_index = menu.index(prev) if prev in menu else 0

            st.selectbox(
                label="",
                options=menu,
                index=default_index,
                key="sidebar_nav",
                help="Choose a section",
                label_visibility="collapsed",
            )

            st.markdown("<div class='ca-sep'></div>", unsafe_allow_html=True)

            # 4) Feedback/Bug Report
            st.markdown("<h3 style='text-align:left;'>🐞 Feedback / Bug Report</h3>", unsafe_allow_html=True)
            with st.form("bugform", clear_on_submit=True):
                bug = st.text_area("Tell us what went wrong or how we can improve.", height=100)
                submitted = st.form_submit_button("Submit")
                if submitted and bug.strip():
                    st.session_state["bug_reports"].append(bug.strip())
                    st.success("Thanks for sharing! We truly appreciate your feedback.")

            st.markdown("<div class='ca-sep'></div>", unsafe_allow_html=True)

            # 5) Clear Chat History
            if st.button("🗑️ Clear Chat", use_container_width=True, key="clear_chat_btn"):
                st.session_state["messages"] = [
                    {"role": "assistant", "content": "Hello!👋 Ask me anything about your rental agreements."}
                ]
                st.toast("Chat history cleared.")

            # Footer
            st.markdown("<div class='ca-sep'></div>", unsafe_allow_html=True)
            st.markdown("<div class='ca-footer'>⚡ Powered by Casa Amigo © 2025</div>", unsafe_allow_html=True)

    # === CHAT HANDLERS =====
    def _display_chat_history(self):
        for msg in st.session_state["messages"]:
            role = msg["role"]
            content = msg["content"]
            avatar = self.user_icon if role == "user" else self.idle_icon
            bubble_class = "ca-user" if role == "user" else "ca-assist"
            with st.chat_message(role, avatar=avatar):
                st.markdown(f'<div class="ca-bubble {bubble_class}">{content}</div>', unsafe_allow_html=True)

    # ---- Text + Voice input handler ----
    def _handle_user_input(self):
        """
        Natural bottom chat bar + voice toolbar above it.
        Typing bubble stays until replaced by the final answer.
        """
        # Voice defaults (unchanged)
        st.session_state.setdefault("voice_enabled", False)
        st.session_state.setdefault("tts_voice", "nova")
        st.session_state.setdefault("last_audio_length", 0)

        # Slim toolbar above the input for the mic
        with st.container():
            mic_col, _ = st.columns([1, 9])
            with mic_col:
                audio_bytes = audiorecorder("🎤", "⏹️", key="audio_recorder")

        # Chat input at the bottom
        text_query = st.chat_input("Type your message...")

        user_query = None

        # Voice path (only new audio)
        try:
            audio_len = len(audio_bytes) if audio_bytes else 0
        except Exception:
            audio_len = 0

        if audio_bytes and audio_len > 0 and audio_len != st.session_state["last_audio_length"]:
            st.session_state["last_audio_length"] = audio_len
            with st.spinner("🎤 Transcribing your message..."):
                try:
                    user_query = self.voice_manager.transcribe_audio(audio_bytes)
                except Exception as e:
                    st.error(f"❌ Could not transcribe audio. {e}")
                    user_query = None

        # Text path
        if text_query:
            user_query = text_query
            st.session_state["last_audio_length"] = 0

        if not user_query:
            return

        # Moderation of user input
        try:
            mod_user = moderate_content(user_query, self.config_manager.api_key)
        except Exception as e:
            mod_user = {"is_safe": True, "flagged_categories": [], "error": str(e)}

        # Persist + show user bubble
        st.session_state["messages"].append({"role": "user", "content": user_query})
        with st.chat_message("user", avatar=self.user_icon):
            st.markdown(f'<div class="ca-bubble ca-user">{user_query}</div>', unsafe_allow_html=True)

        # Handle flagged content
        if not mod_user.get("is_safe", True):
            warning_msg = get_moderation_message(mod_user.get("flagged_categories", []))
            reply = (
                f"⚠️ {warning_msg}\n\n"
                "Please rephrase your message to comply with our community guidelines. "
                "Casa Amigo is here to help with rental-related questions in a respectful manner."
            )
            with st.chat_message("assistant", avatar=self.idle_icon):
                st.markdown(f'<div class="ca-bubble ca-assist">{reply}</div>', unsafe_allow_html=True)
            st.session_state["messages"].append({"role": "assistant", "content": reply})
            st.session_state.setdefault("moderation_flags", []).append({
                "timestamp": time.time(),
                "query": user_query,
                "categories": mod_user.get("flagged_categories", [])
            })
            return

        # Generate assistant response with a visible typing bubble
        with st.chat_message("assistant", avatar=self.thinking_icon):
            placeholder = st.empty()
            # keep typing bubble visible until final answer replaces it
            placeholder.markdown(
                "<div class='ca-typing'><span class='ca-dot'></span><span class='ca-dot'></span><span class='ca-dot'></span></div>",
                unsafe_allow_html=True
            )

            try:
                auth = st.session_state.get("auth", {}) or {}
                set_current_auth(auth)
                response = self.chatbot.chat(user_query, auth=auth)
            except Exception as e:
                response = "⚠️ Sorry, something went wrong. Please try again."
                st.toast(f"Backend error: {e}")

            # Safety pass on assistant output
            try:
                mod_assist = moderate_content(response, self.config_manager.api_key)
            except Exception as e:
                mod_assist = {"is_safe": True, "flagged_categories": [], "error": str(e)}

            if not mod_assist.get("is_safe", True):
                response = (
                    "I apologize, but I need to rephrase my response. "
                    "Let me try again with a different approach."
                )

            # Replace typing bubble with final assistant bubble
            placeholder.markdown(f"<div class='ca-bubble ca-assist'>{response}</div>", unsafe_allow_html=True)

            # Optional TTS playback (unchanged)
            if st.session_state.get("voice_enabled", False):
                with st.spinner("🔊 Generating voice response..."):
                    try:
                        voice_name = st.session_state.get("tts_voice", "nova")
                        audio_out = self.voice_manager.text_to_speech(response, voice=voice_name)
                        if audio_out:
                            st.audio(audio_out, format="audio/mp3", autoplay=False)
                        else:
                            st.caption("⚠️ Voice generation failed")
                    except Exception as e:
                        st.caption(f"⚠️ Voice generation failed: {e}")

        # Persist assistant message
        st.session_state["messages"].append({"role": "assistant", "content": response})

        # Debug
        if self.config_manager.get_debug_mode():
            with st.sidebar.expander("🔎 Debug (last turn)", expanded=False):
                st.write("**Input Moderation:**")
                if mod_user.get("error"):
                    st.warning(f"Moderation error: {mod_user['error']}")
                else:
                    st.write(f"✅ Safe: {mod_user.get('is_safe')}")
                    if mod_user.get("flagged_categories"):
                        st.write(f"⚠️ Flagged: {', '.join(mod_user['flagged_categories'])}")

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

    # ===== GATEWAY/LOGIN RENDERING =====
    def _render_gateway(self):
        st.markdown(
            f"""
            <div style="text-align:center; margin-top:1rem;">
                <h2 style="font-size:2rem; color:{self.BLUE}; font-weight:800; margin-bottom:0.5rem;">
                    👋 Welcome to Casa Amigo
                </h2>
                <p style="font-size:1.1rem; color:#555;">
                    Please choose your role and log in to continue.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Custom Tab Styles
        st.markdown(
            """
            <style>
            button[data-baseweb="tab"] {
                font-size: 1.2rem !important;
                font-weight: 700 !important;
                padding: 1rem 2rem !important;
                border-radius: 10px 10px 0 0 !important;
                color: #2C4B8E !important;
                background: #f0f3fa !important;
            }
            button[data-baseweb="tab"]:hover {
                background: #dbe3f8 !important;
                color: #D84339 !important;
            }
            button[data-baseweb="tab"][aria-selected="true"] {
                background: linear-gradient(180deg, #2C4B8E 0%, #D84339 120%) !important;
                color: #ffffff !important;
                font-weight: 800 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        tenant_tab, agent_tab = st.tabs(["Tenant", "Agent"])
        with tenant_tab:
            self._gateway_login("tenant")
        with agent_tab:
            self._gateway_login("agent")

    def _gateway_login(self, role: str):
        st.markdown(
            f"<h3 style='text-align:center; color:{self.RED}; margin-top:0.5rem;'>{role.title()} Login</h3>",
            unsafe_allow_html=True
        )

        email = st.text_input(f"{role.title()} Email", key=f"gw_{role}_email")
        pwd = st.text_input(f"{role.title()} Password", type="password", key=f"gw_{role}_pwd")

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button(
            f"🔐 Login as {role.title()}",
            key=f"gw_{role}_login_btn",
            use_container_width=True
        ):
            if self._api_login(email, pwd):
                st.session_state[f"auth_{role}"] = st.session_state["auth"]
                st.session_state["active_role"] = role
                st.session_state["screen"] = "app"
                # default landings
                st.session_state["sidebar_nav"] = "Conversations" if role == "tenant" else "Dashboard"
                st.toast(f"✅ Logged in as {role.title()}")
                st.rerun()
            else:
                st.error("❌ Login failed. Please check your credentials.")

    # ===== MAIN APP RUNNER =====
    def run(self):
        screen = st.session_state.get("screen", "gateway")
        role = st.session_state.get("active_role")

        if screen == "gateway":
            self._render_gateway()
            return

        if not role:
            st.warning("⚠️ Please log in first.")
            st.session_state["screen"] = "gateway"
            st.rerun()

        # Sidebar
        self._render_sidebar()
        nav = st.session_state.get("sidebar_nav")

        # Logout
        if nav == "Logout":
            st.session_state["screen"] = "gateway"
            st.session_state["active_role"] = None
            st.session_state["auth"] = {"logged_in": False, "email": None}
            st.rerun()

        # ==== AGENT FLOW =====
        if role == "agent":
            if nav == "Dashboard":
                st.markdown("### Listings Dashboard")

                # Fetch from /properties
                props = self._fetch_properties(limit=200, offset=0)

                if not props:
                    st.warning("No properties available from backend yet.")
                else:
                    # Normalize and show a clean metadata table
                    raw_df = pd.json_normalize(props)

                    preferred_cols = [
                        "id", "property_id", "uuid",
                        "title", "name", "address",
                        "district", "area", "neighborhood",
                        "price", "monthly_rent", "rent",
                        "bedrooms", "beds", "bathrooms", "size_sqft", "size_sqm",
                        "mrt_distance_mins", "distance_mrt",
                        "available_from", "created_at", "updated_at"
                    ]
                    ordered_cols = [c for c in preferred_cols if c in raw_df.columns]
                    other_cols = [c for c in raw_df.columns if c not in ordered_cols]
                    display_df = raw_df[ordered_cols + other_cols] if ordered_cols else raw_df

                    st.dataframe(display_df, use_container_width=True, hide_index=True)

                    # Optional CSV Export
                    csv = display_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Download listings CSV",
                        data=csv,
                        file_name="listings_export.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

            elif nav == "Profile":
                auth = st.session_state.get("auth", {}) or {}
                active_role = st.session_state.get("active_role", "agent")
                st.markdown("## Account")
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("Role", active_role.title())
                with c2: st.metric("Email", auth.get("email") or "—")
                with c3: st.metric("User ID", auth.get("user_id") or "—")

        # ==== TENANT FLOW =====
        elif role == "tenant":
            if nav == "Conversations":
                self._display_chat_history()
                self._handle_user_input()

            elif nav == "Profile":
                auth = st.session_state.get("auth", {}) or {}
                active_role = st.session_state.get("active_role", "tenant")

                st.markdown("## Account")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Role", active_role.title())
                with c2:
                    st.metric("Email", auth.get("email") or "—")
                with c3:
                    st.metric("User ID", auth.get("user_id") or "—")

# ===== APP ENTRY POINT =====
if __name__ == "__main__":
    load_dotenv()
    app = StreamlitApp()
    app.run()