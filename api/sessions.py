"""
Session Management - Conversation session handling
"""
from datetime import datetime, timedelta
from typing import Dict
import uuid

# Session storage
conversation_sessions: Dict[str, Dict] = {}
SESSION_TIMEOUT = timedelta(hours=2)


def clean_old_sessions():
    """
    Delete expired conversation sessions.
    """
    now = datetime.now()
    expired_sessions = [
        sid for sid, session in conversation_sessions.items()
        if now - session['last_activity'] > SESSION_TIMEOUT
    ]
    for sid in expired_sessions:
        del conversation_sessions[sid]


def get_or_create_session(session_id: str = None) -> tuple[str, dict]:
    """
    Get existing session or create new one.
    
    Args:
        session_id: Optional session ID
        
    Returns:
        Tuple of (session_id, session_dict)
    """
    if not session_id:
        session_id = str(uuid.uuid4())
    
    clean_old_sessions()
    
    if session_id not in conversation_sessions:
        conversation_sessions[session_id] = {
            'messages': [],
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'links': {},  # question_id -> link list
            'refusals': set(),  # question_ids that were refused
        }
    
    session = conversation_sessions[session_id]
    
    # Ensure links dict exists for backward compatibility
    if 'links' not in session:
        session['links'] = {}
    
    # Ensure refusals set exists for backward compatibility
    if 'refusals' not in session:
        session['refusals'] = set()
    
    session['last_activity'] = datetime.now()
    
    return session_id, session


def reset_session(session_id: str = None):
    """Reset a conversation session"""
    if session_id and session_id in conversation_sessions:
        del conversation_sessions[session_id]
        return {"status": "success", "message": "Session reset"}
    return {"status": "info", "message": "No active session to reset"}


def get_session_info(session_id: str):
    """Get information about a session"""
    if session_id in conversation_sessions:
        session = conversation_sessions[session_id]
        return {
            "exists": True,
            "message_count": len(session['messages']),
            "created_at": session['created_at'].isoformat(),
            "last_activity": session['last_activity'].isoformat()
        }
    return {"exists": False}
