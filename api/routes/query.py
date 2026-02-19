"""
Query Routes - Main query endpoint for streaming responses
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from datetime import datetime
import json
import uuid

from api.models import QueryRequest
from api.sessions import get_or_create_session
from api.logging import save_question_response, contains_medical_disclaimer
from core.query_chromadb import ask_question_stream

router = APIRouter()


@router.post("/query")
async def query_agent(request: QueryRequest):
    """
    Main endpoint to ask questions to the agent and receive streaming responses
    """
    session_id, session = get_or_create_session(request.session_id)
    
    conversation_history = session['messages']
    user_message = {
        'role': 'user',
        'content': request.question,
        'timestamp': datetime.now().isoformat()
    }
    conversation_history.append(user_message)
    
    question_id = str(uuid.uuid4())
    
    def generate():
        # Generate the assistant's streaming response (SSE)
        yield f"data: {json.dumps({'session_id': session_id, 'question_id': question_id, 'chunk': ''})}\n\n"
        
        assistant_response = ""
        is_refusal = False
        
        for chunk in ask_question_stream(
            request.question,
            language=request.language,
            timezone=request.timezone,
            locale=request.locale,
            conversation_history=conversation_history,
            session=session,
            question_id=question_id
        ):
            # Detect refusal marker
            if chunk == "__REFUSAL__":
                is_refusal = True
                continue  # Don't include marker in response
            
            assistant_response += chunk
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        
        # Save question and response to log (including refused ones)
        save_question_response(question_id, request.question, assistant_response)
        
        # Check if response contains medical disclaimer (don't show links)
        has_medical_disclaimer = contains_medical_disclaimer(assistant_response)
        
        # Mark refusal or medical disclaimer in session for links endpoint
        if is_refusal or has_medical_disclaimer:
            session.setdefault('refusals', set()).add(question_id)
        
        # Only add to history if not a refusal
        if not is_refusal:
            assistant_message = {
                'role': 'assistant',
                'content': assistant_response,
                'timestamp': datetime.now().isoformat()
            }
            conversation_history.append(assistant_message)
        else:
            # Remove the user message from history since it was refused
            conversation_history.pop()
        
        # Send links as final SSE event (empty if refusal or medical disclaimer)
        links = session['links'].get(question_id, []) if not (is_refusal or has_medical_disclaimer) else []
        yield f"data: {json.dumps({'links': links})}\n\n"

    return StreamingResponse(
        generate(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )
