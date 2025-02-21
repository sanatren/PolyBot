import sys
import os
import uuid
import streamlit as st
from langchain_core.messages import HumanMessage

# ✅ Adjust Python path to include the `Bot/` directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Bot")))

# ✅ Import chatbot functions
from chatbot_memory import invoke_with_language, get_session_history, set_session_language

# ✅ Custom CSS for a modern, ChatGPT-like interface
st.markdown("""
<style>
/* Global background and font */
body {
    background-color: #f7f7f7;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Sidebar styling */
.css-1d391kg {  /* container for the sidebar */
    background-color: #f0f2f6;
}

/* Chat message styling when using fallback markdown */
.user-msg {
    background-color: #d1e7dd;
    padding: 10px 15px;
    border-radius: 10px;
    margin: 5px 0;
    text-align: right;
}
.assistant-msg {
    background-color: #fff;
    padding: 10px 15px;
    border-radius: 10px;
    margin: 5px 0;
    border: 1px solid #ececec;
}

/* Button styling */
div.stButton > button {
    background-color: #4CAF50;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
}
div.stButton > button:hover {
    background-color: #45a049;
}
</style>
""", unsafe_allow_html=True)

# ✅ Initialize Streamlit session state for multiple chat sessions
if "sessions" not in st.session_state:
    st.session_state.sessions = {}  # store multiple sessions

if "current_session" not in st.session_state:
    st.session_state.current_session = str(uuid.uuid4())  # default session id

if st.session_state.current_session not in st.session_state.sessions:
    st.session_state.sessions[st.session_state.current_session] = {
        "chat_history": [],
        "language": "English"
    }

# ✅ Sidebar: Manage Sessions and Preferred Language
st.sidebar.title("💬 Chat Sessions")

# ➕ New Chat button
if st.sidebar.button("➕ New Chat"):
    new_session_id = str(uuid.uuid4())
    st.session_state.sessions[new_session_id] = {"chat_history": [], "language": "English"}
    st.session_state.current_session = new_session_id
    st.experimental_rerun()

# List existing sessions with a radio button to switch between them
session_ids = list(st.session_state.sessions.keys())
selected_session = st.sidebar.radio("Switch Session", session_ids, index=session_ids.index(st.session_state.current_session))

# 🗑️ Delete Chat button (ensures at least one session remains)
if st.sidebar.button("🗑️ Delete Chat"):
    if len(st.session_state.sessions) > 1:
        del st.session_state.sessions[selected_session]
        st.session_state.current_session = list(st.session_state.sessions.keys())[-1]
        st.experimental_rerun()

# Switch to the selected session if different from the current one
if selected_session != st.session_state.current_session:
    st.session_state.current_session = selected_session

# Preferred language input
st.sidebar.subheader("🌍 Preferred Language")
language = st.sidebar.text_input("Enter your language", 
                                 value=st.session_state.sessions[st.session_state.current_session]["language"])
set_session_language(st.session_state.current_session, language)

# ✅ Main Chat Interface
st.title("🤖 PolyBot")

# Display chat history using new Streamlit chat components if available
chat_history = st.session_state.sessions[st.session_state.current_session]["chat_history"]

if "chat_message" in dir(st):
    # Use Streamlit’s built-in chat message components
    for msg in chat_history:
        if msg["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(msg["message"])
        else:
            with st.chat_message("user"):
                st.markdown(msg["message"])
else:
    # Fallback: custom display with styled markdown messages
    st.write("### Chat History")
    for msg in chat_history:
        if msg["role"] == "assistant":
            st.markdown(f"<div class='assistant-msg'>{msg['message']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='user-msg'>{msg['message']}</div>", unsafe_allow_html=True)

# ✅ User Message Input (using st.chat_input if available)
if "chat_input" in dir(st):
    user_input = st.chat_input("Type your message")
else:
    user_input = st.text_input("Type your message", key="user_input")

# When a message is submitted, invoke the chatbot and update session history
if user_input:
    # Invoke chatbot function with language preference
    response = invoke_with_language(
        session_id=st.session_state.current_session,
        messages=[HumanMessage(content=user_input)],
        language=language
    )
    # Append both user and assistant messages to the chat history
    st.session_state.sessions[st.session_state.current_session]["chat_history"].append(
        {"role": "user", "message": user_input}
    )
    st.session_state.sessions[st.session_state.current_session]["chat_history"].append(
        {"role": "assistant", "message": response}
    )
    st.rerun()
