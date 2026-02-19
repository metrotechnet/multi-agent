"""
Session Routes - Session management endpoints
"""
from fastapi import APIRouter

from api.sessions import reset_session, get_session_info

router = APIRouter()


@router.post("/api/reset_session")
def reset_session_endpoint(session_id: str = None):
    """Reset a conversation session"""
    return reset_session(session_id)


@router.get("/api/session_info")
def get_session_info_endpoint(session_id: str):
    """Get information about a session"""
    return get_session_info(session_id)
