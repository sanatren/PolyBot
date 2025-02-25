import sys
import os
import uuid
import streamlit as st
from langchain_core.messages import HumanMessage
import json
from datetime import datetime, timedelta

# Adjust Python path to include the `Bot/` directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Bot")))

# Import chatbot functions
from chatbot_memory import invoke_with_language, get_session_history, set_session_language
from supabase import create_client  # Import Supabase client

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Custom CSS
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

# Functions for session management with Supabase
def save_session_to_supabase(session_id, session_name, language="English"):
    """Save session metadata to Supabase sessions table"""
    try:
        # Check if session exists
        existing = supabase.table("sessions").select("*").eq("session_id", session_id).execute()
        
        if existing.data:
            # Update existing session
            data = {
                "last_accessed": datetime.now().isoformat(),
                "language": language,
                "name": session_name
            }
            response = supabase.table("sessions").update(data).eq("session_id", session_id).execute()
        else:
            # Create new session
            data = {
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat(),
                "language": language,
                "name": session_name,
            }
            response = supabase.table("sessions").insert(data).execute()
        
        return response
    except Exception as e:
        st.error(f"Error saving session: {e}")
        return None

def get_all_sessions():
    """Retrieve all active sessions from the past week"""
    try:
        # Get sessions from the past week
        one_week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        response = supabase.table("sessions").select("*").gte("last_accessed", one_week_ago).order("last_accessed", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error retrieving sessions: {e}")
        return []

def get_chat_history_from_supabase(session_id):
    """Retrieve chat history for a specific session"""
    try:
        response = supabase.table("history").select("*").eq("session_id", session_id).order("timestamp", desc=False).execute()
        
        # Transform to the format expected by the UI
        chat_history = []
        for msg in response.data:
            chat_history.append({
                "role": msg["role"],
                "message": msg["message"]
            })
        
        return chat_history
    except Exception as e:
        st.error(f"Error retrieving chat history: {e}")
        return []

def delete_session(session_id):
    """Delete a session and its associated messages"""
    try:
        # Delete messages first (foreign key constraint)
        supabase.table("history").delete().eq("session_id", session_id).execute()
        # Then delete the session
        supabase.table("sessions").delete().eq("session_id", session_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting session: {e}")
        return False

# Initialize Streamlit session state
if "current_session" not in st.session_state:
    # Check for existing sessions, otherwise create a new one
    existing_sessions = get_all_sessions()
    
    if existing_sessions:
        # Use the most recent session
        st.session_state.current_session = existing_sessions[0]["session_id"]
        st.session_state.current_session_name = existing_sessions[0].get("name", "Untitled Chat")
        st.session_state.current_language = existing_sessions[0].get("language", "English")
    else:
        # Create a new session
        new_session_id = str(uuid.uuid4())
        st.session_state.current_session = new_session_id
        st.session_state.current_session_name = "New Chat"
        st.session_state.current_language = "English"
        save_session_to_supabase(new_session_id, "New Chat")

# Sidebar: Manage Sessions and Preferred Language
st.sidebar.title("💬 Chat Sessions")

# New Chat button
if st.sidebar.button("➕ New Chat"):
    new_session_id = str(uuid.uuid4())
    st.session_state.current_session = new_session_id
    st.session_state.current_session_name = "New Chat"
    st.session_state.current_language = "English"
    save_session_to_supabase(new_session_id, "New Chat")
    st.rerun()

# List existing sessions with a radio button to switch between them
existing_sessions = get_all_sessions()
session_options = {session["session_id"]: session.get("name", f"Chat {i+1}") 
                  for i, session in enumerate(existing_sessions)}

# Create a mapping of display names to session objects for deletion lookup
session_display_map = {}
for session in existing_sessions:
    display_name = f"{session.get('name', 'Untitled')} ({session['session_id'][:8]}...)"
    session_display_map[display_name] = session

if session_options:
    # Format session names for display
    formatted_options = [f"{name} ({session_id[:8]}...)" for session_id, name in session_options.items()]
    
    # Display sessions as radio buttons
    selected_index = list(session_options.keys()).index(st.session_state.current_session) if st.session_state.current_session in session_options else 0
    selected_option = st.sidebar.radio("Select Session", formatted_options, index=selected_index)
    
    # Extract the session ID from the selected option
    selected_session_id = list(session_options.keys())[formatted_options.index(selected_option)]
    
    # Switch to the selected session if different from the current one
    if selected_session_id != st.session_state.current_session:
        st.session_state.current_session = selected_session_id
        selected_session = next((s for s in existing_sessions if s["session_id"] == selected_session_id), None)
        if selected_session:
            st.session_state.current_session_name = selected_session.get("name", "Untitled Chat")
            st.session_state.current_language = selected_session.get("language", "English")
        st.rerun()

# Session management section
st.sidebar.subheader("Session Management")

# Session name edit field
new_session_name = st.sidebar.text_input("Chat Name", value=st.session_state.current_session_name)
if new_session_name != st.session_state.current_session_name:
    st.session_state.current_session_name = new_session_name
    save_session_to_supabase(st.session_state.current_session, new_session_name, st.session_state.current_language)

# Delete Session Options
if len(existing_sessions) > 1:  # Only show if there's more than one session
    st.sidebar.subheader("Delete Sessions")
    
    # Multi-select for sessions to delete
    sessions_to_delete = st.sidebar.multiselect(
        "Select sessions to delete:",
        options=[f"{session.get('name', 'Untitled')} ({session['session_id'][:8]}...)" for session in existing_sessions],
        help="Select one or more sessions to delete"
    )
    
    # Always show the confirmation checkbox
    confirm_delete = st.sidebar.checkbox("Confirm deletion? This action cannot be undone.")
    
    # Delete button
    if sessions_to_delete and st.sidebar.button("🗑️ Delete Selected Sessions"):
        if not confirm_delete:
            st.sidebar.error("Please confirm deletion by checking the box above.")
        else:
            deleted_any = False
            need_rerun = False
            
            for session_display in sessions_to_delete:
                # Look up the full session object using our map
                if session_display in session_display_map:
                    session = session_display_map[session_display]
                    session_id = session["session_id"]
                    
                    # If deleting current session, flag for rerun and session change
                    if session_id == st.session_state.current_session:
                        need_rerun = True
                    
                    # Delete the session
                    if delete_session(session_id):
                        st.sidebar.success(f"Deleted: {session.get('name', 'Untitled')}")
                        deleted_any = True
            
            if deleted_any:
                if need_rerun:
                    # Get remaining sessions to switch to
                    remaining_sessions = get_all_sessions()
                    if remaining_sessions:
                        st.session_state.current_session = remaining_sessions[0]["session_id"]
                        st.session_state.current_session_name = remaining_sessions[0].get("name", "Untitled Chat")
                        st.session_state.current_language = remaining_sessions[0].get("language", "English")
                st.rerun()

# Delete Current Chat button (ensures at least one session remains)
if st.sidebar.button("🗑️ Delete Current Chat"):
    if len(existing_sessions) > 1:
        if delete_session(st.session_state.current_session):
            # Set current session to the next available session
            remaining_sessions = [s for s in existing_sessions if s["session_id"] != st.session_state.current_session]
            if remaining_sessions:
                st.session_state.current_session = remaining_sessions[0]["session_id"]
                st.session_state.current_session_name = remaining_sessions[0].get("name", "Untitled Chat")
                st.session_state.current_language = remaining_sessions[0].get("language", "English")
            st.rerun()
    else:
        st.sidebar.error("Cannot delete the only remaining session. Create a new session first.")

# Preferred language input
st.sidebar.subheader("🌍 Preferred Language")
language = st.sidebar.text_input("Enter your language", value=st.session_state.current_language)

if language != st.session_state.current_language:
    st.session_state.current_language = language
    set_session_language(st.session_state.current_session, language)
    save_session_to_supabase(st.session_state.current_session, st.session_state.current_session_name, language)

# Main Chat Interface
st.title("🤖 PolyBot")
st.subheader(st.session_state.current_session_name)

# Retrieve and display chat history for the current session
chat_history = get_chat_history_from_supabase(st.session_state.current_session)

if "chat_message" in dir(st):
    # Use Streamlit's built-in chat message components
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

# User Message Input
if "chat_input" in dir(st):
    user_input = st.chat_input("Type your message")
else:
    user_input = st.text_input("Type your message", key="user_input")

# When a message is submitted, invoke the chatbot
if user_input:
    # Invoke chatbot function with language preference
    response = invoke_with_language(
        session_id=st.session_state.current_session,
        messages=[HumanMessage(content=user_input)],
        language=language
    )
    
    # Update last accessed timestamp
    save_session_to_supabase(
        st.session_state.current_session, 
        st.session_state.current_session_name,
        language
    )
    
    st.rerun()