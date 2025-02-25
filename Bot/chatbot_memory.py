import os
import sys
import uuid
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from supabase import create_client


load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")


supabase = create_client(supabase_url, supabase_key)

model = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=openai_api_key)

session_data = {}

def get_session_history(session_id: str):
    """Retrieves chat history for a session, initializing if necessary."""
    if session_id not in session_data:
        session_data[session_id] = {"history": [], "language": "English"}
    return session_data[session_id]["history"]

def set_session_language(session_id: str, language: str = "English"):
    """Stores the preferred response language for a given session."""
    if session_id not in session_data:
        session_data[session_id] = {"history": [], "language": language}
    else:
        session_data[session_id]["language"] = language

def save_message_to_supabase(session_id, role, message):
    """Stores chat messages in Supabase."""
    data = {
        "session_id": session_id,
        "role": role,
        "message": message,
    }
    response = supabase.table("history").insert(data).execute()
    return response

def invoke_with_language(session_id: str, messages, language=None):
    """Handles chatbot invocation while ensuring memory & language persistence."""

  
    if session_id not in session_data:
        set_session_language(session_id, "English")

    if language:
        set_session_language(session_id, language)
    else:
        language = session_data[session_id]["language"]

   
    for msg in messages:
        save_message_to_supabase(session_id, "user", msg.content)

    
    existing_messages = get_session_history(session_id)

    
    session_data[session_id]["history"].extend(messages)

    
    response = model.invoke(
        [
            HumanMessage(content=f"Respond in {language}: " + msg.content)
            for msg in session_data[session_id]["history"]
        ]
    )

    
    save_message_to_supabase(session_id, "assistant", response.content)

    return response.content