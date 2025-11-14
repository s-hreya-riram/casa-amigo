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
            /* === FIX FOR SIDEBAR COLLAPSE BUTTON === */
            /* Hide the Material icon text "keyboard_double_arrow_left" */
            [data-testid="stIconMaterial"] {{
                font-size: 0 !important;
            }}

            /* Hide text in collapse button specifically */
            button[kind="headerNoPadding"] [data-testid="stIconMaterial"] {{
                font-size: 0 !important;
                color: transparent !important;
            }}

            /* Keep button functional but hide text content */
            button[kind="headerNoPadding"] span {{
                font-size: 0 !important;
                line-height: 0 !important;
            }}

            /* Clean, simple collapse button */
            button[kind="headerNoPadding"] {{
                width: 2rem !important;
                height: 2rem !important;
                background: transparent !important;
                border: none !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                position: relative !important;
                transition: opacity 0.2s ease !important;
                opacity: 0.7 !important;
            }}

            /* Subtle hover effect */
            button[kind="headerNoPadding"]:hover {{
                opacity: 1 !important;
            }}

            /* Simple chevron - sidebar open */
            button[kind="headerNoPadding"]::before {{
                content: "‹" !important;
                font-size: 1.8rem !important;
                color: #808080 !important;
                position: absolute !important;
                left: 50% !important;
                top: 50% !important;
                transform: translate(-50%, -50%) !important;
                line-height: 1 !important;
                font-weight: 300 !important;
            }}

            /* Simple chevron - sidebar collapsed */
            [data-testid="stSidebar"][aria-expanded="false"] button[kind="headerNoPadding"]::before {{
                content: "›" !important;
            }}
            /* === END SIDEBAR COLLAPSE FIX === */

            .block-container {{
                padding-top: 1.1rem;
                padding-bottom: 2rem;
                background: #FFFFFF;
            }}

            /* === SIDEBAR STYLING - CONSISTENT TYPOGRAPHY === */
            [data-testid="stSidebar"] > div:first-child {{
                background: linear-gradient(180deg, {self.NAVY} 0%, {self.BLUE} 55%, {self.RED} 130%);
                color: #FFFFFF;
                font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
            }}

            /* All text elements in sidebar - unified styling */
            [data-testid="stSidebar"] h1, 
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3, 
            [data-testid="stSidebar"] h4,
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] .stCaption,
            [data-testid="stSidebar"] .stSuccess,
            [data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p,
            [data-testid="stSidebar"] span {{
                color: #FFFFFF !important;
                font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif !important;
                font-weight: 500 !important;
            }}

            /* Headings hierarchy */
            [data-testid="stSidebar"] h1 {{
                font-size: 1.8rem !important;
                font-weight: 700 !important;
                margin: 1rem 0 0.8rem 0 !important;
            }}

            [data-testid="stSidebar"] h2 {{
                font-size: 1.4rem !important;
                font-weight: 650 !important;
                margin: 0.8rem 0 0.6rem 0 !important;
            }}

            [data-testid="stSidebar"] h3 {{
                font-size: 1.1rem !important;
                font-weight: 600 !important;
                margin: 0.6rem 0 0.5rem 0 !important;
            }}

            /* Regular text */
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] label {{
                font-size: 0.9rem !important;
                font-weight: 500 !important;
                line-height: 1.4 !important;
                margin: 0.3rem 0 !important;
            }}

            /* Captions and small text */
            [data-testid="stSidebar"] .stCaption,
            [data-testid="stSidebar"] small {{
                font-size: 0.8rem !important;
                font-weight: 400 !important;
                opacity: 0.9 !important;
                margin: 0.2rem 0 !important;
            }}

            /* Success messages */
            [data-testid="stSidebar"] .stSuccess {{
                font-size: 0.85rem !important;
                font-weight: 500 !important;
                background: rgba(72, 187, 120, 0.2) !important;
                border-left: 3px solid #48bb78 !important;
                padding: 0.5rem !important;
                border-radius: 6px !important;
                margin: 0.5rem 0 !important;
            }}

            /* Form labels */
            [data-testid="stSidebar"] .stTextArea label,
            [data-testid="stSidebar"] .stTextInput label,
            [data-testid="stSidebar"] .stSelectbox label {{
                font-size: 0.9rem !important;
                font-weight: 600 !important;
                color: rgba(255, 255, 255, 0.95) !important;
                margin-bottom: 0.3rem !important;
            }}

            /* Motto/tagline */
            .ca-tagline-strong {{
                text-align: center !important;
                font-style: italic !important;
                color: #FFFFFF !important;
                opacity: 0.95 !important;
                margin: 0.4rem 0 0.8rem 0 !important;
                line-height: 1.4 !important;
                font-weight: 600 !important;
                font-size: 0.95rem !important;
                font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif !important;
            }}

            /* Voice section text */
            .voice-hint {{
                color: rgba(255,255,255,0.9) !important;
                font-size: 0.88rem !important;
                line-height: 1.5 !important;
                margin-bottom: 0.7rem !important;
                display: flex !important;
                align-items: center !important;
                gap: 0.5rem !important;
                font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif !important;
                font-weight: 500 !important;
            }}

            /* Footer */
            .ca-footer {{ 
                text-align: center !important; 
                font-size: 0.85rem !important; 
                color: rgba(255,255,255,0.8) !important; 
                margin-top: 1rem !important;
                font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif !important;
                font-weight: 500 !important;
            }}

            /* Separators */
            [data-testid="stSidebar"] hr,
            [data-testid="stSidebar"] .ca-sep {{
                border: none !important; 
                border-top: 1px solid rgba(255,255,255,0.25) !important;
                margin: 0.8rem 0 !important;
            }}

            /* === FORM ELEMENTS IN SIDEBAR === */
            
            /* Red focus for textareas and chat input */
            [data-testid="stSidebar"] textarea,
            [data-testid="stChatInput"] textarea {{
                background: #FFFFFF !important; 
                color: #000 !important;
                border: 2px solid {self.RED}80 !important; 
                border-radius: 10px !important;
                font-size: 0.9rem !important; 
                padding: 0.6rem 1rem !important;
                outline: none !important; 
                box-shadow: none !important;
                transition: border 0.15s ease-in-out;
                font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif !important;
            }}
            
            [data-testid="stSidebar"] textarea:focus,
            [data-testid="stChatInput"] textarea:focus {{
                border: 2px solid {self.RED} !important;
                box-shadow: 0 0 6px {self.RED}60 !important;
            }}

            /* Selectbox styling */
            [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {{
                border-radius: 12px !important;
                font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif !important;
            }}
            
            [data-testid="stSidebar"] .stSelectbox {{
                margin-top: 0.4rem !important;
                margin-bottom: 0.6rem !important;
            }}

            /* Global button reset */
            .stButton > button {{
                border-radius: 999px !important;
                font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif !important;
                font-weight: 600 !important;
                font-size: 0.9rem !important;
                padding: 0.6rem 1.2rem !important;
                border: none !important;
                cursor: pointer !important;
                transition: all 0.15s ease-in-out !important;
            }}

            /* Sidebar buttons */
            [data-testid="stSidebar"] .stButton > button {{
                background: linear-gradient(90deg, #D84339, #B7352D) !important;
                color: #FFFFFF !important;
                width: 100% !important;
                display: block !important;
                box-shadow: 0 4px 10px rgba(0,0,0,0.18) !important;
                margin-top: 0.3rem !important;
            }}

            [data-testid="stSidebar"] .stButton > button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(0,0,0,0.25) !important;
                opacity: 0.96;
            }}

            /* Clear Chat button */
            #clear-chat-container .stButton > button {{
                background: linear-gradient(90deg, #D84339, #B7352D) !important;
                color: #FFFFFF !important;
                border: none !important;
                border-radius: 999px !important;
                padding: 0.65rem 1.2rem !important;
                font-weight: 700 !important;
                font-size: 0.9rem !important;
                width: 100% !important;
                box-shadow: 0 4px 10px rgba(0,0,0,0.18) !important;
                transition: all 0.15s ease-in-out !important;
            }}

            #clear-chat-container .stButton > button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(0,0,0,0.25) !important;
                opacity: 0.96;
            }}


            /* Submit button */
            [data-testid="stSidebar"] .stFormSubmitButton > button {{
                background: linear-gradient(90deg, #D84339, #B7352D) !important;
                color: #FFFFFF !important;
                border: none !important;
                border-radius: 999px !important;
                padding: 0.65rem 1.2rem !important;
                font-weight: 700 !important;
                font-size: 0.9rem !important;
                width: 100% !important;
                box-shadow: 0 4px 10px rgba(0,0,0,0.18) !important;
                transition: all 0.15s ease-in-out !important;
                margin-top: 0.3rem !important;
            }}

            [data-testid="stSidebar"] .stFormSubmitButton > button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(0,0,0,0.25) !important;
                opacity: 0.96;
            }}

            /* Submit button -> to match the styling */
            #bugform-wrapper .stButton > button {{
                background: linear-gradient(90deg, #D84339, #B7352D) !important;
                color: #FFFFFF !important;
                border: none !important;
                border-radius: 999px !important;
                padding: 0.65rem 1.2rem !important;
                font-weight: 700 !important;
                font-size: 0.9rem !important;
                width: 100% !important;
                box-shadow: 0 4px 10px rgba(0,0,0,0.18) !important;
                transition: all 0.15s ease-in-out !important;
            }}

            #bugform-wrapper .stButton > button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(0,0,0,0.25) !important;
                opacity: 0.96;
            }}

            /* Gateway Login Buttons */
            .gateway-login-btn > button {{
                background: linear-gradient(90deg, #2C4B8E, #D84339) !important;
                color: #FFFFFF !important;
                font-size: 1.05rem !important;
                font-weight: 700 !important;
                padding: 0.85rem 1.4rem !important;
                border-radius: 12px !important;
                border: none !important;
                width: 100% !important;
                box-shadow: 0 4px 10px rgba(0,0,0,0.12) !important;
                transition: all 0.2s ease-out !important;
            }}

            .gateway-login-btn > button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(0,0,0,0.2) !important;
                opacity: 0.95;
            }}

            /* Force solid red buttons in sidebar, including Clear Chat */
            [data-testid="stSidebar"] button[kind="secondary"],
            [data-testid="stSidebar"] button[kind="primary"] {{
                background: linear-gradient(90deg, #D84339, #B7352D) !important;
                color: #FFFFFF !important;
                border: none !important;
                box-shadow: 0 4px 10px rgba(0,0,0,0.18) !important;
                opacity: 1 !important;
            }}

            /* === MAIN CONTENT STYLING === */

            /* Chat bubbles */
            .ca-bubble {{
                border-radius: 18px; 
                padding: 14px 16px; 
                margin: 6px 0;
                color: #0A0A0A; 
                backdrop-filter: blur(6px); 
                -webkit-backdrop-filter: blur(6px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
            }}
            .ca-user {{ 
                background: rgba(216, 67, 57, 0.08); 
                border-left: 4px solid {self.RED}; 
            }}
            .ca-assist {{ 
                background: rgba(44, 75, 142, 0.08); 
                border-left: 4px solid {self.BLUE}; 
            }}

            /* Avatars larger & circular */
            [data-testid="stChatMessage"] img {{
                border-radius: 50% !important; 
                border: 3px solid #fff;
                width: 70px !important; 
                height: 70px !important; 
                object-fit: cover;
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
                display:inline-block; 
                width:6px; 
                height:6px; 
                margin:0 2px;
                background:{self.BLUE}; 
                border-radius:50%; 
                animation: ca-bounce 1s infinite;
            }}
            .ca-dot:nth-child(2) {{ animation-delay: .15s; }}
            .ca-dot:nth-child(3) {{ animation-delay: .3s; }}
            @keyframes ca-bounce {{
                0%, 80%, 100% {{ transform: scale(1); opacity:.6; }}
                40% {{ transform: scale(1.6); opacity:1; }}
            }}

            .ca-main-footer {{ 
                text-align:center; 
                font-size:.85rem; 
                color:#666; 
                margin-top:14px; 
                opacity:.8; 
            }}

            /* === VOICE SECTION AUDIO RECORDER === */
            
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

    def _api_base(self) -> str:
        """Determines the base API URL"""
        try:
            if "api" in st.secrets and "base_url" in st.secrets["api"]:
                return st.secrets["api"]["base_url"].rstrip("/")
        except Exception:
            pass
        return os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")
  
    def _api_login(self, email: str, password: str, user_type: str | None = None):
        """
        Login wrapper.

        Frontend passes `user_type` based on selected role:

        - "tenant"         -> users.user_type = 'tenant'         (map to tenant_profiles)
        - "property_agent" -> users.user_type = 'property_agent' (map to property_agent)
        """
        API_BASE = self._api_base()
        email = (email or "").strip()
        password = (password or "").strip()

        if not email or not password:
            st.error("Email and password are required.")
            return False

        try:
            # Build params for backend call
            params = {"email": email, "password": password}
            if user_type:
                params["user_type"] = user_type

            r = requests.post(
                f"{API_BASE}/auth/login",
                params=params,
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()

            token = data.get("access_token") or data.get("token")
            user_id = data.get("user_id")
            backend_user_type = data.get("user_type") or user_type

            # Verify role matches
            if user_type and backend_user_type and backend_user_type != user_type:
                st.error(
                    f"Role mismatch: you tried to log in as '{user_type}', "
                    f"but this account is registered as '{backend_user_type}'. "
                    "Please choose the correct tab (Tenant/Agent) for this account."
                )
                return False

            if token:
                auth_data = {
                    "token": token,
                    "user_id": str(user_id),
                    "email": data.get("email", email),
                    "user_type": backend_user_type,
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

    def _fetch_tenant_profile(self, user_id: str | None = None) -> dict | None:
        """
        Fetch the tenant profile for the logged-in user.
        Uses GET /tenantprofiles/{user_id}
        """
        if not user_id:
            return None
        data = self._get_json(f"/tenantprofiles/{user_id}", fallback=None)
        return data

    def _fetch_tenant_preferences(self, user_id: str | None = None) -> list[dict]:
        """
        Fetch tenant's property preferences using GET /preferences/{user_id}.
        Backend can return:
        - a list
        - a single dict
        - or {"preferences": [...]}
        """
        if not user_id:
            return []

        data = self._get_json(f"/preferences/{user_id}", fallback=None)
        if not data:
            return []

        # If backend returns a plain list
        if isinstance(data, list):
            return data

        # If backend wraps it, e.g. {"preferences": [...]}
        if isinstance(data, dict) and "preferences" in data:
            prefs = data["preferences"]
            return prefs if isinstance(prefs, list) else [prefs]

        # If backend returns a single row dict
        if isinstance(data, dict):
            return [data]

        return []

    def _fetch_tenancy_agreements(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """
        Fetch tenancy agreements for agents from GET /tenancy-agreements.
        """
        data = self._get_json(
            "/tenancy-agreements",
            params={"limit": limit, "offset": offset},
            fallback={"agreements": []},
        )
        if isinstance(data, dict):
            return data.get("agreements", [])
        return data or []
    
    def _clean_df_for_display(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove embedding or vector-like columns from any DataFrame before showing in UI.
        """
        if df is None or df.empty:
            return df

        df = df.copy()
        known_vector_cols = [
            "embedding",
            "embeddings",
            "content_vector",
            "agreement_embeddings",
            "agreement_embedding",
            "tenant_embedding",
            "document_embedding",
            "chunk_embedding",
            "vector",
            "vectors",
        ]

        drop_cols = [c for c in known_vector_cols if c in df.columns]

        # Extra safety: auto-detect list-of-floats columns (typical embedding pattern)
        for col in df.columns:
            if col in drop_cols:
                continue
            col_series = df[col].dropna()
            if col_series.empty:
                continue
            first_val = col_series.iloc[0]
            # Check if it's a long list/tuple of numbers -> likely an embedding
            if isinstance(first_val, (list, tuple)) and len(first_val) > 10:
                # Check first few elements are numeric
                numeric_like = all(
                    isinstance(x, (int, float)) for x in list(first_val)[:20]
                )
                if numeric_like:
                    drop_cols.append(col)

        if drop_cols:
            df = df.drop(columns=drop_cols)

        return df

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
    
    def _auth_headers(self):
        auth = st.session_state.get("auth", {}) or {}
        token = auth.get("token")
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

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
            tenant_menu = ["Dashboard", "Conversations", "Profile", "Logout"]
            agent_menu  = ["Dashboard", "Profile", "Logout"]
            menu = tenant_menu if role == "tenant" else agent_menu

            prev = st.session_state.get("sidebar_nav")
            default_index = menu.index(prev) if prev in menu else 0

            st.selectbox(
                label="Section",
                options=menu,
                index=default_index,
                key="sidebar_nav",
                help="Choose a section",
                label_visibility="collapsed",
            )

            st.markdown("<div class='ca-sep'></div>", unsafe_allow_html=True)

            auth = st.session_state["auth"]
            if auth["logged_in"]:
                st.markdown(
                    f"<p style='color: #FFFFFF; font-size: 0.9rem; font-weight: 500; margin: 0.5rem 0;'>✅ Signed in as <span style='color: #FFFFFF; font-weight: 600;'>{auth.get('email') or 'user'}</span></p>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    "<p style='color: rgba(255,255,255,0.8); font-size: 0.9rem; font-weight: 400; margin: 0.5rem 0;'>🔒 Not signed in</p>",
                    unsafe_allow_html=True
                )

            st.divider()

            # 4) Voice Input Section --> ONLY for tenants
            if role == "tenant":
                st.markdown("<div class='voice-section'>", unsafe_allow_html=True)
                col1, col2 = st.columns([3.25, 1])
                with col1:
                    st.markdown(
                        "<p class='voice-hint'>Prefer to speak? Record your message instead of typing.</p>",
                        unsafe_allow_html=True
                    )
                with col2:
                    audio_bytes = audiorecorder("🔴", "⏹️", key="sidebar_voice")
                st.markdown("</div>", unsafe_allow_html=True)

                # Process voice input only if it's new audio
                if audio_bytes and len(audio_bytes) > 0:
                    try:
                        from io import BytesIO
                        audio_buffer = BytesIO()
                        audio_bytes.export(audio_buffer, format="wav")
                        audio_data = audio_buffer.getvalue()

                        current_audio_hash = hash(audio_data)
                        last_audio_hash = st.session_state.get("last_audio_hash", None)

                        if current_audio_hash != last_audio_hash:
                            st.session_state["last_audio_hash"] = current_audio_hash
                            with st.spinner("Transcribing..."):
                                transcribed_text = self.voice_manager.transcribe_audio(audio_bytes)

                            if transcribed_text:
                                st.session_state["pending_voice_query"] = transcribed_text
                                st.rerun()
                            else:
                                st.error("Could not transcribe. Please try again.")
                    except Exception as e:
                        st.error(f"Error processing audio: {e}")

                st.divider()

            # 5) Feedback/Bug Report
            st.markdown("<h3 style='text-align:left;'>🐞 Feedback/Bug Report</h3>", unsafe_allow_html=True)

            st.markdown("<div id='bugform-wrapper'>", unsafe_allow_html=True)
            with st.form("bugform", clear_on_submit=True):
                bug = st.text_area("Tell us what went wrong or how we can improve.", height=100)
                submitted = st.form_submit_button("Submit")
                if submitted and bug.strip():
                    st.session_state["bug_reports"].append(bug.strip())
                    st.success("Thanks for sharing! We truly appreciate your feedback.")
            st.markdown("</div>", unsafe_allow_html=True)

            # 6) Chat Controls --> ONLY for tenants
            if role == "tenant":
                st.markdown("<div class='ca-sep'></div>", unsafe_allow_html=True)
                st.markdown("<h3 style='text-align:left;'>💬 Chat Controls</h3>", unsafe_allow_html=True)
                st.markdown(
                    "<p style='font-size:0.85rem; opacity:0.9; margin-bottom:0.35rem;'>Reset the conversation and start fresh.</p>",
                    unsafe_allow_html=True,
                )
                st.markdown("<div id='clear-chat-container'>", unsafe_allow_html=True)
                if st.button("🗑️ Clear Chat History", key="clear_chat_btn"):
                    st.session_state["messages"] = [
                        {"role": "assistant", "content": "Hello!👋 Ask me anything about your rental agreements."}
                    ]
                    st.toast("Chat history cleared.")
                st.markdown("</div>", unsafe_allow_html=True)

            # 7) Footer
            st.markdown("<div class='ca-sep'></div>", unsafe_allow_html=True)
            st.markdown("<div class='ca-footer'>⚡ Powered by Casa Amigo © 2025</div>", unsafe_allow_html=True)

    # ===== CHAT HANDLERS =====
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
        
        # Handle text input - ADD UNIQUE KEY
        if user_query := st.chat_input("Type your message...", key="main_chat_input"):
            self._process_query(user_query)
            st.rerun()

    # ===== GATEWAY/LOGIN RENDERING =====
    def _render_gateway(self):
        # footer below chat box
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
            help="Enter your email and password to continue.",
            type="primary",
            use_container_width=True,
        ):
            # Map the frontend role to backend user_type
            mapped_type = "tenant" if role == "tenant" else "property_agent"

            if self._api_login(email, pwd, mapped_type):
                st.session_state[f"auth_{role}"] = st.session_state["auth"]
                st.session_state["active_role"] = role
                st.session_state["screen"] = "app"

                # default landings
                st.session_state["sidebar_nav"] = "Dashboard"

                st.toast(f"✅ Logged in as {role.title()}")
                st.rerun()
            else:
                st.error("❌ Login failed. Please check your credentials.")

    def _render_tenant_profile_card(self, profile: dict):
        """
        Shows display for tenant profile instead of a raw table.
        """
        if not profile:
            st.info("No tenant profile found yet.")
            st.caption("Once your profile is created in `tenant_profiles`, it will appear here.")
            return

        label_map = {
            "full_name": "Full Name",
            "nationality": "Nationality",
            "date_of_birth": "Date of Birth",
            "occupation": "Occupation",
            "employment_status": "Employment Status",
            "household_income": "Household Income",
            "income": "Income",
            "preferred_move_in_date": "Preferred Move-in Date",
            "current_address": "Current Address",
            "family_size": "Household Size",
            "has_pets": "Has Pets",
            "pet_details": "Pet Details",
            "smoking": "Smoker",
            "budget_min": "Budget (Min)",
            "budget_max": "Budget (Max)",
        }

        # Hide IDs, timestamps, embeddings, etc.
        hidden_keys = {
            "profile_id", "id", "user_id", "created_at", "updated_at",
            "embedding", "embeddings", "tenant_embedding", "vector", "vectors",
        }

        items = []
        for key, value in profile.items():
            if key in hidden_keys:
                continue
            label = label_map.get(key, key.replace("_", " ").title())
            items.append((label, value))

        if not items:
            st.info("Profile exists but has no visible fields yet.")
            return

        col1, col2 = st.columns(2)
        for i, (label, value) in enumerate(items):
            col = col1 if i % 2 == 0 else col2
            with col:
                st.markdown(
                    f"""
                    <div style="
                        border-radius: 10px;
                        padding: 10px 12px;
                        margin-bottom: 8px;
                        background-color: #F7FAFC;
                        border: 1px solid #E2E8F0;
                    ">
                        <div style="font-size: 0.8rem; color:#718096; text-transform:uppercase; letter-spacing:0.03em;">
                            {label}
                        </div>
                        <div style="font-size: 0.95rem; font-weight:600; color:#1A202C; margin-top:2px;">
                            {value if (value not in [None, ""]) else "—"}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    
    def _render_preferences_cards(self, prefs: list[dict] | dict):
        """
        Renders each row as profile-style cards.
        """
        if not prefs:
            st.info("No saved property preferences yet.")
            return

        # Normalize to list
        if isinstance(prefs, dict):
            prefs = [prefs]

        label_map = {
            "min_budget": "💰 Budget (Min)",
            "max_budget": "💰 Budget (Max)",
            "budget_min": "💰 Budget (Min)",
            "budget_max": "💰 Budget (Max)",
            "min_bedrooms": "🛏 Min Bedrooms",
            "max_bedrooms": "🛏 Max Bedrooms",
            "preferred_areas": "📍 Preferred Areas",
            "max_mrt_walk_mins": "🚉 Max Walk to MRT (mins)",
            "property_type": "🏢 Property Type",
            "room_type": "🚪 Room Type",
            "furnishing": "🛋 Furnishing",
            "pets_allowed": "🐾 Pets Allowed",
            "smoking_allowed": "🚭 Smoking Allowed",
            "aircon_required": "❄️ Aircon Required",
            "lease_term_months": "📆 Lease Term (months)",
        }

        hidden_keys = {
            "id", "preference_id", "user_id", "tenant_id",
            "created_at", "updated_at",
            "embedding", "embeddings", "preference_embedding", "vector", "vectors",
        }


        for idx, pref in enumerate(prefs, start=1):
            st.markdown(f"##### Preference Set #{idx}")

            col1, col2 = st.columns(2)
            items = []

            for key, value in pref.items():
                if key in hidden_keys:
                    continue
                label = label_map.get(key, key.replace("_", " ").title())
                
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                items.append((label, value))

            if not items:
                st.caption("No visible fields in this preference set.")
                continue

            for i, (label, value) in enumerate(items):
                col = col1 if i % 2 == 0 else col2
                with col:
                    st.markdown(
                        f"""
                        <div style="
                            border-radius: 10px;
                            padding: 10px 12px;
                            margin-bottom: 8px;
                            background-color: #F7FAFC;
                            border: 1px solid #E2E8F0;
                        ">
                            <div style="font-size: 0.8rem; color:#718096;
                                        text-transform:uppercase; letter-spacing:0.03em;">
                                {label}
                            </div>
                            <div style="font-size: 0.95rem; font-weight:600;
                                        color:#1A202C; margin-top:2px;">
                                {value if (value not in [None, '']) else '—'}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            st.markdown("---")

    def _render_tenancy_agreements_cards(self, agreements: list[dict] | dict):
        """
        Shows display for tenancy agreements on the Agent dashboard.
        """
        if not agreements:
            st.info("No tenancy agreements found yet.")
            return

        # Normalize to list
        if isinstance(agreements, dict):
            agreements = [agreements]

        label_map = {
            "status": "📌 Status",
            "start_date": "📆 Start Date",
            "end_date": "📆 End Date",
            "monthly_rent": "💰 Monthly Rent",
            "deposit_amount": "💵 Deposit Amount",
            "tenant_id": "👤 Tenant ID",
            "tenant_email": "✉️ Tenant Email",
            "property_id": "🏢 Property ID",
            "created_at": "🕒 Created At",
            "updated_at": "🕒 Updated At",
        }

        hidden_keys = {
            "id", "agreement_id",
            "embedding", "embeddings", "agreement_embedding", "agreement_embeddings", "vector", "vectors",
        }

        for idx, ag in enumerate(agreements, start=1):
            # Try to build a nice heading
            title = ag.get("property_title") or ag.get("property_name")
            addr  = ag.get("property_address") or ag.get("address")
            heading_parts = []
            if title: heading_parts.append(str(title))
            if addr: heading_parts.append(str(addr))
            heading = " • ".join(heading_parts) if heading_parts else f"Agreement #{idx}"

            st.markdown(f"#### 📄 {heading}")

            col1, col2 = st.columns(2)
            items = []

            for key, value in ag.items():
                if key in hidden_keys:
                    continue
                label = label_map.get(key, key.replace("_", " ").title())
                items.append((label, value))

            for i, (label, value) in enumerate(items):
                col = col1 if i % 2 == 0 else col2
                with col:
                    st.markdown(
                        f"""
                        <div style="
                            border-radius: 10px;
                            padding: 10px 12px;
                            margin-bottom: 8px;
                            background-color: #F7FAFC;
                            border: 1px solid #E2E8F0;
                        ">
                            <div style="font-size: 0.8rem; color:#718096;
                                        text-transform:uppercase; letter-spacing:0.03em;">
                                {label}
                            </div>
                            <div style="font-size: 0.95rem; font-weight:600;
                                        color:#1A202C; margin-top:2px;">
                                {value if (value not in [None, '']) else '—'}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            st.markdown("---")

    # ===== MAIN APP RUNNER =====
    def run(self):
        screen = st.session_state.get("screen", "gateway")
        role = st.session_state.get("active_role")

        # 1) Gateway (pre-login)
        if screen == "gateway":
            self._render_gateway()
            return

        # 2) Post-login check
        if not role:
            st.warning("⚠️ Please log in first.")
            st.session_state["screen"] = "gateway"
            st.rerun()

        # 3) Sidebar
        self._render_sidebar()
        nav = st.session_state.get("sidebar_nav")

        # 4) Logout handler
        if nav == "Logout":
            st.session_state["screen"] = "gateway"
            st.session_state["active_role"] = None
            st.session_state["auth"] = {"logged_in": False, "email": None}
            st.rerun()
            
        # 5) Agent flow
        if role == "agent":
            if nav == "Dashboard":
                st.markdown("### Agent Dashboard")

                listings_tab, agreements_tab = st.tabs(["📋 Listings", "📄 Tenancy Agreements"])

                with listings_tab:
                    props = self._fetch_properties(limit=200, offset=0)

                    if not props:
                        st.warning("No properties available from backend yet.")
                    else:
                        raw_df = pd.json_normalize(props)
                        raw_df = self._clean_df_for_display(raw_df)

                        # Preferred / ordered columns for the listings table
                        preferred_cols = [
                            "address", "rent", "property_type",
                            "num_bedrooms", "num_bathrooms", "bedrooms",
                            "sqft", "rent_psf", "mrt_info", "listing_status",
                            "property_id", "title", "name",
                            "district", "area", "neighborhood",
                            "price", "monthly_rent", "rent", "bedrooms",
                            "beds", "bathrooms", "size_sqft", "size_sqm",
                            "mrt_distance_mins", "distance_mrt",
                            "available_from", "created_at", "updated_at",
                        ]

                        preferred_cols = [c for c in preferred_cols if c in raw_df.columns]

                        seen = set()
                        ordered_cols = []
                        for c in preferred_cols:
                            if c not in seen:
                                ordered_cols.append(c)
                                seen.add(c)

                        other_cols = [c for c in raw_df.columns if c not in ordered_cols]

                        display_df = raw_df[ordered_cols + other_cols] if ordered_cols else raw_df

                        st.dataframe(
                            display_df,
                            width="stretch",
                            hide_index=True,
                        )

                        # Optional CSV export
                        csv = display_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "Download Listings CSV",
                            data=csv,
                            file_name="listings_export.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )
                
                with agreements_tab:
                    st.markdown("#### Tenancy Agreements")

                    agreements = self._fetch_tenancy_agreements(limit=200, offset=0)

                    if not agreements:
                        st.info("No tenancy agreements found yet.")
                    else:
                        self._render_tenancy_agreements_cards(agreements)

                        agreements_df = pd.json_normalize(agreements)
                        agreements_df = self._clean_df_for_display(agreements_df)

                        preferred_ag_cols = [
                            "id", "agreement_id",
                            "property_id", "property.title", "property.address",
                            "tenant_id", "tenant_email",
                            "status", "start_date", "end_date",
                            "monthly_rent", "deposit_amount",
                            "created_at", "updated_at",
                        ]
                        ordered_ag_cols = [c for c in preferred_ag_cols if c in agreements_df.columns]
                        other_ag_cols = [c for c in agreements_df.columns if c not in ordered_ag_cols]
                        agreements_display = agreements_df[ordered_ag_cols + other_ag_cols] if ordered_ag_cols else agreements_df

                        # Optional CSV export
                        csv_ag = agreements_display.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "Download Agreements CSV",
                            data=csv_ag,
                            file_name="tenancy_agreements_export.csv",
                            mime="text/csv",
                            use_container_width=True,
                            key="download_agreements_btn",
                        )

            elif nav == "Profile":
                auth = st.session_state.get("auth", {}) or {}
                active_role = st.session_state.get("active_role", "agent")
                st.markdown("## Account")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Role", active_role.title())
                with c2:
                    st.metric("Email", auth.get("email") or "—")
                with c3:
                    st.metric("User ID", auth.get("user_id") or "—")

                st.markdown(f"**User Type:** `{auth.get('user_type') or '—'}`")

         # 6) Tenant flow
        elif role == "tenant":
            auth = st.session_state.get("auth", {}) or {}
            user_id = auth.get("user_id")

            # DASHBOARD VIEWING
            if nav == "Dashboard":
                st.markdown("### Tenant Dashboard")
                st.markdown("#### 🏠 Property Preferences")
                prefs = self._fetch_tenant_preferences(user_id=user_id)
                self._render_preferences_cards(prefs)

            # CONVERSATIONS VIEWING
            elif nav == "Conversations":
                self._display_chat_history()
                self._handle_user_input()

            # PROFILE VIEWING
            elif nav == "Profile":
                active_role = st.session_state.get("active_role", "tenant")

                st.markdown("## Account")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Role", active_role.title())
                with c2:
                    st.metric("Email", auth.get("email") or "—")
                with c3:
                    st.metric("User ID", user_id or "—")

                st.markdown(f"**User Type:** `{auth.get('user_type') or '—'}`")

                st.markdown("---")
                st.markdown("### Tenant Profile")

                profile = self._fetch_tenant_profile(user_id=user_id)
                self._render_tenant_profile_card(profile)

# ===== APP ENTRY POINT =====
if __name__ == "__main__":
    load_dotenv()
    app = StreamlitApp()
    app.run()