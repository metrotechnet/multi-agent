
# =====================================================
# Imports - Importations des modules nécessaires
# =====================================================
from fastapi import FastAPI, Body, Query, Request, APIRouter
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from core.query_chromadb import ask_question_stream, get_collection, get_pmids_from_contexts, client
from core.pipeline_gdrive import run_pipeline
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, Optional
import json
import uuid
from datetime import datetime, timedelta
import threading

 # Chargement des variables d'environnement depuis le bon emplacement
# =====================================================
# Configuration & Constantes
# =====================================================
PROJECT_ROOT = Path(__file__).parent
env_path = PROJECT_ROOT / '.env'
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="Personal AI Agent")

# Mount static files and templates with absolute paths
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))

conversation_sessions: Dict[str, Dict] = {}
SESSION_TIMEOUT = timedelta(hours=2)


QUESTION_LOG_PATH = PROJECT_ROOT / "question_log.json"
question_log_lock = threading.Lock()

######################################################
# Fonctions utilitaires
######################################################

def save_question_response(question_id, question, response):
    """
    Sauvegarde une question et sa réponse dans le fichier journal.
    """
    entry = {
        "question_id": question_id,
        "question": question,
        "response": response,
        "timestamp": datetime.now().isoformat(),
        "comments": []
    }
    with question_log_lock:
        try:
            if QUESTION_LOG_PATH.exists():
                with open(QUESTION_LOG_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = []
        except Exception:
            data = []
        data.append(entry)
        with open(QUESTION_LOG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def add_comment_to_question(question_id, comment):
    """Add a comment to a question by id."""
    """
    Ajoute un commentaire à une question par son identifiant.
    """
    with question_log_lock:
        try:
            if QUESTION_LOG_PATH.exists():
                with open(QUESTION_LOG_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                return False
        except Exception:
            return False
        for entry in data:
            if entry.get("question_id") == question_id:
                # Remplace tous les commentaires par le nouveau commentaire
                entry["comments"] = [{
                    "comment": comment,
                    "timestamp": datetime.now().isoformat()
                }]
                with open(QUESTION_LOG_PATH, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return True
        return False


######################################################
# Modèles de données
######################################################
class QueryRequest(BaseModel):
    question: str
    language: str = "fr"
    timezone: str = "UTC"
    locale: str = "fr-FR"
    session_id: Optional[str] = None

######################################################
# Endpoints API
######################################################
# Stocke les PMIDs par session/question pour une récupération ultérieure
@app.post("/query")
# Endpoint principal pour poser une question à l'agent et recevoir une réponse en streaming
async def query_agent(request: QueryRequest):
    session_id = request.session_id or str(uuid.uuid4())
    _clean_old_sessions()
    if session_id not in conversation_sessions:
        conversation_sessions[session_id] = {
            'messages': [],
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'pmids': {},  # question_id -> pmid list
        }
    session = conversation_sessions[session_id]
    # Ensure pmids dict exists for backward compatibility
    if 'pmids' not in session:
        session['pmids'] = {}
    conversation_history = session['messages']
    user_message = {
        'role': 'user',
        'content': request.question,
        'timestamp': datetime.now().isoformat()
    }
    conversation_history.append(user_message)
    session['last_activity'] = datetime.now()
    question_id = str(uuid.uuid4())
    def generate():
        # Génère la réponse de l'assistant en streaming (SSE)
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

    return StreamingResponse(
        generate(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


# Fetch PMIDs for a session/question if available, else fallback to old behavior
@app.post("/api/pmids")
# Endpoint pour obtenir les PMIDs pertinents à une question
def get_pmids_api(
    session_id: str = Body(None),
    question_id: str = Body(None),
    question: str = Body(None),
    top_k: int = 5
):
    # Try to fetch from session memory first
    if session_id and question_id:
        session = conversation_sessions.get(session_id)
        if session and 'pmids' in session and question_id in session['pmids']:
            return {"pmids": session['pmids'][question_id]}
    # Fallback: recompute from question
    if not question:
        return {"pmids": []}
    col = get_collection()
    if col is None:
        return {"error": "ChromaDB collection not available"}
    query_emb = client.embeddings.create(
        model="text-embedding-3-large",
        input=question
    ).data[0].embedding
    results = col.query(
        query_embeddings=[query_emb],
        n_results=top_k
    )
    contexts = results['documents'][0] if results['documents'] and results['documents'][0] else []
    pmids = get_pmids_from_contexts(contexts)
    return {"pmids": pmids}

@app.post("/api/add_comment")
# Endpoint pour ajouter un commentaire à une question
def add_comment_api(
    question_id: str = Body(...),
    comment: str = Body(...)
):
    success = add_comment_to_question(question_id, comment)
    if success:
        return {"status": "success", "message": "Comment added"}
    else:
        return {"status": "error", "message": "Question ID not found"}
@app.post("/api/like_answer")
# Endpoint pour liker ou disliker une réponse
def like_answer(
    question_id: str = Body(...),
    like: bool = Body(...)
):
    """Add a like or dislike to a question by id. Stores as a list of likes/dislikes (for possible multiple votes)."""
    with question_log_lock:
        try:
            if QUESTION_LOG_PATH.exists():
                with open(QUESTION_LOG_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                return {"status": "error", "message": "Log file not found"}
        except Exception:
            return {"status": "error", "message": "Could not read log file"}
        for entry in data:
            if entry.get("question_id") == question_id:
                if "likes" not in entry:
                    entry["likes"] = []
                entry["likes"].append({
                    "like": like,
                    "timestamp": datetime.now().isoformat()
                })
                with open(QUESTION_LOG_PATH, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return {"status": "success", "message": "Vote recorded"}
        return {"status": "error", "message": "Question ID not found"}    
    
@app.get("/api/download_log")
# Endpoint pour télécharger le journal des questions (admin seulement)
def download_question_log(key: str = Query(...)):
    if key != "dboubou363":
        return {"status": "error", "message": "Unauthorized"}
    if not QUESTION_LOG_PATH.exists():
        return {"status": "error", "message": "Log file not found"}
    return FileResponse(
        path=str(QUESTION_LOG_PATH),
        filename="question_log.json",
        media_type="application/json"
    )

@app.get("/log_report", response_class=HTMLResponse)
# Endpoint pour afficher le rapport du journal (admin seulement)
def serve_log_report(request: Request, key: str = Query(...)):
    # Only allow access if key is correct
    if key != "dboubou363":
        return HTMLResponse("<h3 style='color:red;text-align:center;margin-top:2em'>Unauthorized: Invalid key</h3>", status_code=401)
    return templates.TemplateResponse("log_report.html", {"request": request})

######################################################
# Gestion des sessions
######################################################
def _clean_old_sessions():
    """
    Supprime les sessions de conversation expirées.
    """
    now = datetime.now()
    expired_sessions = [
        sid for sid, session in conversation_sessions.items()
        if now - session['last_activity'] > SESSION_TIMEOUT
    ]
    for sid in expired_sessions:
        del conversation_sessions[sid]

@app.get("/", response_class=HTMLResponse)
######################################################
# Endpoints divers
######################################################
def home(request: Request):
    """
    Sert la page principale d'accueil.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health():
    """
    Endpoint de vérification de l'état de santé de l'application.
    """
    return {"status": "ok"}

@app.get("/api/get_config")
def get_translations():
    """
    Récupère les traductions pour le frontend.
    """
    try:
        translations_path = Path(__file__).parent / "config" / "config.json"
        with open(translations_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        return translations
    except FileNotFoundError:
        return {"error": "config not found"}
    except Exception as e:
        return {"error": f"Error loading config: {str(e)}"}

@app.post("/api/reset_session")
# Endpoint pour réinitialiser une session de conversation
def reset_session(session_id: str = None):
    """Reset a conversation session"""
    if session_id and session_id in conversation_sessions:
        del conversation_sessions[session_id]
        return {"status": "success", "message": "Session reset"}
    return {"status": "info", "message": "No active session to reset"}

@app.get("/api/session_info")
# Endpoint pour obtenir les informations d'une session
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

@app.post("/update")
# Endpoint pour déclencher l'indexation des documents Google Drive
def update_pipeline(request: Request):
    """
    Endpoint to trigger Google Drive document indexing pipeline.
    Called by Cloud Scheduler daily at 3 AM.
    """
    try:
        print(f"[{datetime.now().isoformat()}] Pipeline update triggered")
        print(f"User-Agent: {request.headers.get('user-agent', 'Unknown')}")
        
        result = run_pipeline()
        
        if result.get("error"):
            print(f"❌ Pipeline error: {result['error']}")
            return {
                "status": "error",
                "message": result['error'],
                "authenticated": result.get("authenticated", False)
            }
        
        processed = result.get("processed", 0)
        total = result.get("total", 0)
        
        print(f"✅ Pipeline completed: {processed}/{total} documents processed")
        
        return {
            "status": "success",
            "message": f"Pipeline executed successfully",
            "processed": processed,
            "total": total,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"❌ Pipeline exception: {str(e)}")
        return {
            "status": "error",
            "message": f"Pipeline failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
