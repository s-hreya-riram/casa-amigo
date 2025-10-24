import os
import time
from typing import List, Dict, Any, Optional

import streamlit as st
from dotenv import load_dotenv
from config import ConfigManager
from core import ChatbotEngine, DocumentIndexManager


# -------------------------
# Utilities (dev helpers)
# -------------------------
def init_session_key(key: str, default_val):
    if key not in st.session_state:
        st.session_state[key] = default_val


# -------------------------
# Main App
# -------------------------
class StreamlitApp:
    """Casa Amigo – role-based single-file app (Tenant-first, light Agent view)"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.doc_manager = DocumentIndexManager()
        self.chatbot = ChatbotEngine(self.doc_manager.index, self.config_manager.api_key)

        self._setup_page()
        self._init_session_state()
        self._render_sidebar()

    # -------------------------
    # Page & State
    # -------------------------
    def _setup_page(self):
        st.set_page_config(page_title="Casa Amigo", page_icon="🏠", layout="wide")
        st.title("🏠 Casa Amigo - Rental Assistant")

    def _init_session_state(self):
        # Auth-ish state (dev simulation)
        init_session_key("user_email", "")
        init_session_key("role", "tenant")  # "tenant" | "agent"

        # Routing state (per-role)
        init_session_key("tenant_page", "Home")  # "Home" | "Chat" | "Profile"
        init_session_key("agent_page", "Dashboard")  # "Dashboard" | "Conversations"

        # Chat state (tenant chat)
        init_session_key("messages", [
            {"role": "assistant", "content": "Hello 👋! Ask me anything about your rental agreements."}
        ])
        init_session_key("current_conversation_id", "demo-conv-001")  # placeholder

        # Mock data for Agent view (read-only)
        init_session_key("agent_conversations", [
            {
                "id": "conv-001",
                "tenant_email": "alice@example.com",
                "last_message": "What’s the standard deposit for a 1BR near Tiong Bahru?",
                "updated_at": "2025-10-15 14:21",
                "status": "open"
            },
            {
                "id": "conv-002",
                "tenant_email": "ben@nus.edu.sg",
                "last_message": "Could we schedule a viewing for Saturday 11am?",
                "updated_at": "2025-10-16 09:10",
                "status": "open"
            },
            {
                "id": "conv-003",
                "tenant_email": "charlie@gmail.com",
                "last_message": "Any 2BR options under 4k at Queenstown?",
                "updated_at": "2025-10-17 18:47",
                "status": "pending"
            },
        ])
        init_session_key("agent_selected_conversation", "conv-001")

    # -------------------------
    # Sidebar (role + navigation)
    # -------------------------
    def _render_sidebar(self):
        with st.sidebar:
            st.markdown("### 👤 Dev Login")
            st.text_input("Email", key="user_email", placeholder="you@domain.com")
            st.selectbox("Role", ["tenant", "agent"], key="role")

            st.divider()
            if st.session_state["role"] == "tenant":
                st.markdown("### 🧭 Tenant Navigation")
                st.radio(
                    "Go to",
                    ["Home", "Chat", "Profile"],
                    key="tenant_page",
                    horizontal=True
                )
            else:
                st.markdown("### 🧭 Agent Navigation")
                st.radio(
                    "Go to",
                    ["Dashboard", "Conversations"],
                    key="agent_page",
                    horizontal=True
                )

            with st.expander("⚙️ Settings"):
                if st.button("Clear tenant chat history"):
                    st.session_state["messages"] = [
                        {"role": "assistant", "content": "Chat cleared. How can I help you now? 🙂"}
                    ]
                    st.toast("Cleared chat history.")

    # -------------------------
    # Top-level Router
    # -------------------------
    def run(self):
        role = st.session_state["role"]
        if role == "agent":
            self._route_agent()
        else:
            self._route_tenant()

    # -------------------------
    # Tenant Routes & Pages
    # -------------------------
    def _route_tenant(self):
        page = st.session_state["tenant_page"]
        if page == "Home":
            self._tenant_home()
        elif page == "Chat":
            self._tenant_chat()
        elif page == "Profile":
            self._tenant_profile()
        else:
            st.error("Unknown tenant page.")

    def _tenant_home(self):
        st.subheader("🏡 Tenant Home")
        st.write("Search quickly or jump into chat.")

        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        with col1:
            query = st.text_input("Search (area, budget, bedrooms…)", placeholder="e.g., Tiong Bahru 1BR under 4k")
        with col2:
            st.selectbox("Bedrooms", ["Any", "1", "2", "3+"])
        with col3:
            st.selectbox("Budget (max)", ["Any", "3000", "4000", "5000", "7000"])
        with col4:
            st.selectbox("Walk to MRT (mins)", ["Any", "5", "10", "15"])

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔎 Quick Search", use_container_width=True):
                st.info("Search is mocked for now — connect Supabase when schema is finalized.")

        with c2:
            if st.button("💬 Open Chat", use_container_width=True):
                st.session_state["tenant_page"] = "Chat"
                st.rerun()

        st.markdown("#### Quick chips")
        st.write(
            "• Near **Queenstown** • Under **$4k** • **2BR** • Walk ≤ **10 mins** to MRT"
        )
        st.caption("These are placeholders for UX—wire filters later to your search endpoint.")

    def _display_chat_history(self):
        for message in st.session_state["messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    def _tenant_chat(self):
        st.subheader("💬 Tenant Chat")
        self._display_chat_history()

        user_input = st.chat_input("Type your message…")
        if user_input:
            # append user message
            st.session_state["messages"].append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            # assistant response with typing indicator
            with st.chat_message("assistant"):
                thinking = st.empty()
                thinking.write("_Assistant is typing…_")
                try:
                    # Simulate brief latency; remove or reduce if undesirable
                    time.sleep(0.2)
                    response = self.chatbot.ask(user_input)
                except Exception as e:
                    response = "⚠️ Sorry, something went wrong. Please try again."
                    st.toast("Backend error (mock): {}".format(str(e)))
                thinking.empty()
                st.markdown(response)

            st.session_state["messages"].append({"role": "assistant", "content": response})

        # small footer actions
        st.write("")
        cols = st.columns(3)
        with cols[0]:
            if st.button("🧹 Clear chat"):
                st.session_state["messages"] = [
                    {"role": "assistant", "content": "Chat cleared. How can I help you now? 🙂"}
                ]
                st.rerun()
        with cols[1]:
            st.caption(f"Conversation ID: `{st.session_state['current_conversation_id']}` (mock)")
        with cols[2]:
            st.caption(f"Logged in as: {st.session_state.get('user_email') or 'guest'}")

    def _tenant_profile(self):
        st.subheader("👤 Tenant Profile (mock)")
        email = st.session_state.get("user_email") or "guest@local"
        st.write(f"**Email:** {email}")
        st.write("**Preferences (mock):** 2BR • Budget ≤ $4k • ≤ 10-min walk to MRT • Queenstown/Redhill")
        st.info("Connect this to `user_profiles` later. Keep this page read-only for now.")

    # -------------------------
    # Agent Routes & Pages (Light)
    # -------------------------
    def _route_agent(self):
        page = st.session_state["agent_page"]
        if page == "Dashboard":
            self._agent_dashboard()
        elif page == "Conversations":
            self._agent_conversations()
        else:
            st.error("Unknown agent page.")

    def _agent_dashboard(self):
        st.subheader("🗂️ Agent Dashboard (light)")
        st.caption("Read-only preview to validate the end-to-end flow.")

        convs = st.session_state["agent_conversations"]
        open_count = sum(1 for c in convs if c["status"] == "open")
        pending_count = sum(1 for c in convs if c["status"] == "pending")

        k1, k2, k3 = st.columns(3)
        k1.metric("Open Conversations", open_count)
        k2.metric("Pending Actions", pending_count)
        k3.metric("My Assignment (mock)", "2")

        st.markdown("### 🏘️ Recommended Listings (mock)")

        listings = [
            {
                "name": "SkyVue Residences, Bishan",
                "price": "$3,800 / mo",
                "bedrooms": "2BR",
                "distance": "6 min walk to Bishan MRT",
                "relevance": "95%",
            },
            {
                "name": "Commonwealth Towers",
                "price": "$4,200 / mo",
                "bedrooms": "2BR",
                "distance": "3 min walk to Queenstown MRT",
                "relevance": "91%",
            },
            {
                "name": "The Anchorage, Redhill",
                "price": "$3,600 / mo",
                "bedrooms": "1BR",
                "distance": "8 min walk to Redhill MRT",
                "relevance": "87%",
            },
        ]

        for prop in listings:
            with st.container(border=True):
                st.write(f"**{prop['name']}** — {prop['price']}")
                st.caption(f"{prop['bedrooms']} • {prop['distance']}")
                st.progress(int(prop['relevance'].replace('%','')))

        st.markdown("### Recent conversations")
        for c in convs:
            with st.container(border=True):
                st.write(f"**{c['tenant_email']}** • `{c['id']}` • Updated: {c['updated_at']} • Status: **{c['status']}**")
                st.write(f"_“{c['last_message']}”_")
                if st.button("Open", key=f"open_{c['id']}", use_container_width=True):
                    st.session_state["agent_selected_conversation"] = c["id"]
                    st.session_state["agent_page"] = "Conversations"
                    st.rerun()

        st.info("Later: wire this to `conversations` (agent_id), add filters & pagination.")

    def _agent_conversations(self):
        st.subheader("💼 Conversations (read-only)")
        convs = {c["id"]: c for c in st.session_state["agent_conversations"]}
        current = convs.get(st.session_state["agent_selected_conversation"])

        cols = st.columns([1, 2])
        with cols[0]:
            st.markdown("#### Inbox")
            for c in st.session_state["agent_conversations"]:
                label = f"{c['tenant_email']} • {c['id']} • {c['status']}"
                if st.button(label, key=f"select_{c['id']}", use_container_width=True):
                    st.session_state["agent_selected_conversation"] = c["id"]
                    st.rerun()

        with cols[1]:
            st.markdown("#### Conversation")
            if not current:
                st.warning("Select a conversation on the left.")
                return

            st.write(f"**ID:** `{current['id']}`")
            st.write(f"**Tenant:** {current['tenant_email']}")
            st.write(f"**Last update:** {current['updated_at']}")
            st.write(f"**Status:** **{current['status']}**")

            st.markdown("---")
            st.caption("Messages (mocked):")
            # Minimal static thread preview (replace with DB later)
            thread = [
                {"role": "user", "content": current["last_message"]},
                {"role": "assistant", "content": "Happy to help! Are you available this Saturday for a viewing?"},
            ]
            for m in thread:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

            st.info("This view is read-only for this phase. Next: enable claim/assign & reply via agent role.")


# Entry

if __name__ == "__main__":
    load_dotenv()
    app = StreamlitApp()
    app.run()
