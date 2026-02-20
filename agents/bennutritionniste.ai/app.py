
# =====================================================
# Imports - Importations des modules nécessaires
# =====================================================
from fastapi import FastAPI, Body, Query, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from core.query_chromadb import ask_question_stream, get_collection, get_pmids_from_contexts, is_substantial_question, client
from core.pipeline_gdrive import run_pipeline
from core.translate import translate_text_stream, transcribe_audio_whisper, translate_audio_whisper, get_supported_languages
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, Optional
import json
import uuid
from datetime import datetime, timedelta
import threading
import re as re_tts
import os


def _generate_tts_audio(text, language):
    """Generate TTS audio from text. Returns audio bytes or None on error."""
    try:
        import openai
        client_tts = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        clean = text
        clean = re_tts.sub(r'\*\*(.+?)\*\*', r'\1', clean)
        clean = re_tts.sub(r'\*(.+?)\*', r'\1', clean)
        clean = re_tts.sub(r'#{1,6}\s', '', clean)
        clean = re_tts.sub(r'```[\s\S]*?```', '', clean)
        clean = re_tts.sub(r'`([^`]+)`', r'\1', clean)
        clean = re_tts.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
        clean = re_tts.sub(r'PMID:\s*\d+', '', clean, flags=re_tts.IGNORECASE)
        clean = re_tts.sub(r'\[\d+\]', '', clean)
        clean = re_tts.sub(r'R\u00e9f\u00e9rences?\s*PubMed\s*:.*$', '', clean, flags=re_tts.MULTILINE|re_tts.IGNORECASE)
        clean = re_tts.sub(r'References?\s*:.*$', '', clean, flags=re_tts.MULTILINE|re_tts.IGNORECASE)
        clean = re_tts.sub(r'Sources?\s*:.*$', '', clean, flags=re_tts.MULTILINE|re_tts.IGNORECASE)
        clean = re_tts.sub(r'\n{2,}', '. ', clean)
        clean = re_tts.sub(r'\n', ' ', clean)
        clean = re_tts.sub(r'\s{2,}', ' ', clean)
        clean = clean.strip()[:4096]
        if not clean:
            return None
        voice = "nova" if language in ["fr", "es", "it", "pt", "ro"] else "alloy"
        tts_resp = client_tts.audio.speech.create(
            model="tts-1", voice=voice, input=clean, response_format="mp3"
        )
        audio_bytes = b""
        for audio_chunk in tts_resp.iter_bytes(4096):
            audio_bytes += audio_chunk
        return audio_bytes
    except Exception as e:
        print(f"TTS generation error: {e}")
        return None


def _tts_thread_worker(session, question_id, text, language):
    """Background worker that generates TTS and stores result in session."""
    audio_bytes = _generate_tts_audio(text, language)
    if audio_bytes:
        session.setdefault('tts_audio', {})[question_id] = audio_bytes
    else:
        session.setdefault('tts_audio', {})[question_id] = b''  # Empty = failed

 # Chargement des variables d'environnement depuis le bon emplacement
# =====================================================
# Configuration & Constantes
# =====================================================
PROJECT_ROOT = Path(__file__).parent
env_path = PROJECT_ROOT / '.env'
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="Dok2u Multi Agent")

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

def contains_medical_disclaimer(response_text):
    """
    Détecte si la réponse contient des phrases suggérant de consulter un professionnel.
    Retourne True si la réponse ne mérite pas de PMIDs (disclaimer médical présent).
    """
    if not response_text:
        return False
    
    response_lower = response_text.lower()
    
    # Patterns français
    french_patterns = [
        'consulter un professionnel',
        'consulte un professionnel',
        'consultez un professionnel',
        'consulter votre médecin',
        'consultez votre médecin',
        'parler à un médecin',
        'parlez à un médecin',
        'voir un médecin',
        'voyez un médecin',
        'demander conseil à un professionnel',
        'demandez conseil à un professionnel',
        'avis médical',
        'consultation médicale',
        'professionnel de santé',
        'professionnel de la santé',
        'nutritionniste',
        'diététicien',
    ]
    
    # Patterns anglais
    english_patterns = [
        'consult a professional',
        'consult your doctor',
        'see a doctor',
        'talk to a doctor',
        'speak to a doctor',
        'seek medical advice',
        'medical consultation',
        'health professional',
        'healthcare professional',
        'nutritionist',
        'dietitian',
    ]
    
    all_patterns = french_patterns + english_patterns
    
    # Vérifier si au moins un pattern est présent
    for pattern in all_patterns:
        if pattern in response_lower:
            return True
    
    return False


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
    tts: bool = False

class TranslateRequest(BaseModel):
    text: str
    target_language: str = "en"
    source_language: str = "auto"

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
            'refusals': set(),  # question_ids that were refused
        }
    session = conversation_sessions[session_id]
    # Ensure pmids dict exists for backward compatibility
    if 'pmids' not in session:
        session['pmids'] = {}
    # Ensure refusals set exists for backward compatibility
    if 'refusals' not in session:
        session['refusals'] = set()
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
        
        # Check if response contains medical disclaimer (don't show PMIDs)
        has_medical_disclaimer = contains_medical_disclaimer(assistant_response)
        
        # Mark refusal or medical disclaimer in session for PMID endpoint
        if is_refusal or has_medical_disclaimer:
            session.setdefault('refusals', set()).add(question_id)
        
        # Start TTS generation in background thread if requested
        if request.tts and assistant_response:
            tts_thread = threading.Thread(
                target=_tts_thread_worker,
                args=(session, question_id, assistant_response, request.language),
                daemon=True
            )
            tts_thread.start()
            yield f"data: {json.dumps({'tts_pending': question_id})}\n\n"
        
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


@app.post("/api/tts_result")
def get_tts_result(
    session_id: str = Body(...),
    question_id: str = Body(...)
):
    """Return TTS audio if ready, or 202 if still generating."""
    from fastapi.responses import Response
    session = conversation_sessions.get(session_id)
    if not session:
        return JSONResponse({"status": "not_found"}, status_code=404)
    tts_store = session.get('tts_audio', {})
    if question_id not in tts_store:
        return JSONResponse({"status": "pending"}, status_code=202)
    audio_bytes = tts_store.pop(question_id)  # Remove after serving
    if not audio_bytes:
        return JSONResponse({"status": "failed"}, status_code=500)
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Length": str(len(audio_bytes))}
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
    # Try to fetch from session memory first (PMIDs already computed during streaming)
    if session_id and question_id:
        session = conversation_sessions.get(session_id)
        if session:
            # Check if this question was refused
            if question_id in session.get('refusals', set()):
                return {"pmids": []}
            
            # Return stored PMIDs
            if 'pmids' in session and question_id in session['pmids']:
                return {"pmids": session['pmids'][question_id]}
        
    # Fallback: recompute from question if not in cache
    if not question:
        return {"pmids": []}
    
    # Don't return PMIDs for non-substantial questions
    if not is_substantial_question(question):
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
        n_results=top_k,
        include=['documents', 'metadatas']
    )
    contexts = results['documents'][0] if results['documents'] and results['documents'][0] else []
    metadatas = results['metadatas'][0] if results.get('metadatas') and results['metadatas'][0] else []
    pmids = get_pmids_from_contexts(contexts, metadatas=metadatas)
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
    """Add or update a like/dislike vote for a question. Replaces any previous vote."""
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
                entry["likes"] = {
                    "like": like,
                    "timestamp": datetime.now().isoformat()
                }
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

@app.get("/api/languages")
# Endpoint pour obtenir la liste des langues supportées pour la traduction
def get_languages():
    """Return the list of supported translation languages."""
    return get_supported_languages()


@app.post("/api/translate")
# Endpoint pour traduire du texte en streaming
async def translate_text_endpoint(request: TranslateRequest):
    """Translate text to target language using GPT with streaming."""
    def generate():
        translated = ""
        for chunk in translate_text_stream(
            text=request.text,
            target_language=request.target_language,
            source_language=request.source_language
        ):
            translated += chunk
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/transcribe_audio")
async def transcribe_audio_endpoint(
    audio: UploadFile = File(...),
    language: str = Form(None)
):
    """
    Transcribe audio using Whisper (speech recognition only).
    Returns just the transcribed text without translation.
    
    Args:
        audio: Audio file to transcribe
        language: Optional ISO-639-1 language code (e.g., 'en', 'fr') for better accuracy
    """
    audio_bytes = await audio.read()
    transcribed_text = transcribe_audio_whisper(
        audio_bytes, 
        filename=audio.filename or "audio.webm",
        language=language
    )
    
    if not transcribed_text:
        return JSONResponse({"error": "Could not transcribe audio"}, status_code=400)
    
    return JSONResponse({"text": transcribed_text})


@app.post("/api/translate_audio")
# Endpoint pour transcrire et traduire de l'audio via Whisper
async def translate_audio_endpoint(
    audio: UploadFile = File(...),
    target_language: str = Form("en"),
    source_language: str = Form("auto")
):
    """
    Transcribe audio using Whisper, then translate result to target language.
    Step 1: Whisper transcribes the audio
    Step 2: GPT translates the transcription to the target language
    """
    audio_bytes = await audio.read()
    
    # Step 1: Transcribe with Whisper
    transcribed_text = transcribe_audio_whisper(audio_bytes, filename=audio.filename or "audio.webm")
    
    if not transcribed_text:
        return JSONResponse({"error": "Could not transcribe audio"}, status_code=400)
    
    # Step 2: Translate the transcribed text
    def generate():
        # First send the transcription
        yield f"data: {json.dumps({'transcription': transcribed_text, 'chunk': ''})}\n\n"
        for chunk in translate_text_stream(
            text=transcribed_text,
            target_language=target_language,
            source_language=source_language
        ):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/tts")
async def text_to_speech(
    text: str = Body(..., embed=True),
    language: str = Body("fr", embed=True)
):
    """
    Convert text to speech using OpenAI TTS API.
    Returns audio/mpeg stream.
    """
    import openai
    import os
    from fastapi.responses import Response
    try:
        client_openai = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Choose voice based on language
        voice = "nova" if language in ["fr", "es", "it", "pt", "ro"] else "alloy"
        response = client_openai.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text[:4096],  # TTS API limit
            response_format="mp3"
        )
        
        # Read full audio content
        audio_bytes = b""
        for chunk in response.iter_bytes(chunk_size=4096):
            audio_bytes += chunk
        
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Length": str(len(audio_bytes)),
                "Content-Disposition": "inline"
            }
        )
    except Exception as e:
        print(f"TTS error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


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
