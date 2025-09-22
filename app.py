import streamlit as st

st.title("🏠 Casa Amigo - Chatbot Prototype")

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# User input
user_input = st.chat_input("Ask a question...")

if user_input:
    # Fake response for now
    response = f"Echo: {user_input}"
    
    st.session_state.chat_history.append(("You", user_input))
    st.session_state.chat_history.append(("Bot", response))

# Display chat history
for role, text in st.session_state.chat_history:
    with st.chat_message("assistant" if role == "Bot" else "user"):
        st.write(text)
