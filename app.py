
# =====================================================
# Imports - Importations des modules nécessaires
# =====================================================
from logging import config
from fastapi import FastAPI, Body, Query, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core.query_chromadb import ask_question_stream, get_collection, get_links_from_contexts, is_substantial_question, client
from core.pipeline_gdrive import run_pipeline
from core.translate import translate_text_stream, transcribe_audio_whisper, translate_audio_whisper, get_supported_languages
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, Optional
import json
import uuid
from datetime import datetime, timedelta
import threading
import os

 # Chargement des variables d'environnement depuis le bon emplacement
# =====================================================
# Configuration & Constantes
# =====================================================
PROJECT_ROOT = Path(__file__).parent
env_path = PROJECT_ROOT / '.env'
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="IMX Multi Agent")

# Configure CORS to allow Firebase hosting domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://imx-multi-agent.web.app",
        "https://imx-multi-agent.firebaseapp.com",
        "http://localhost:3000",  # Local frontend dev server
        "http://localhost:8080",  # Local backend dev server
        "http://localhost:5000",
        "http://127.0.0.1:3000",  # Local frontend dev server
        "http://127.0.0.1:8080",  # Local backend dev server
        "http://127.0.0.1:5000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    Retourne True si la réponse ne mérite pas de liens (disclaimer médical présent).
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

class TranslateRequest(BaseModel):
    text: str
    target_language: str = "en"
    source_language: str = "auto"

######################################################
# Endpoints API
######################################################
# Stocke les liens par session/question pour une récupération ultérieure

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


def deep_merge(base_config: dict, override_config: dict) -> dict:
    """
    Deep merge two configuration dictionaries.
    Override values take precedence over base values.
    
    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary
        
    Returns:
        Merged configuration dictionary
    """
    result = base_config.copy()
    
    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = deep_merge(result[key], value)
        else:
            # Override value
            result[key] = value
    
    return result

@app.get("/api/get_config")
def get_translations(agent: Optional[str] = None):
    """
    Get configuration with optional agent-specific overrides.
    
    Args:
        agent: Optional agent name ('nutria' or 'translator')
        
    Returns:
        Configuration dictionary (merged if agent specified)
    """
    try:
        # Load the main shared configuration
        main_config_path = Path(__file__).parent / "knowledge-bases" / "common" / "common.json"
        main_config = {}
        if main_config_path.exists():
            with open(main_config_path, 'r', encoding='utf-8') as f:
                main_config = json.load(f)

        # If no agent specified, return shared config
        if not agent:
            return main_config
        
        # Load agent-specific configuration
        agent_config_path = None
        # Load shared configuration
        if agent == "common":
            agent_config_path = Path(__file__).parent / "knowledge-bases" / "common" / "config.json"
        elif agent == "nutria":
            agent_config_path = Path(__file__).parent / "knowledge-bases" / "nutria" / "config.json"
        elif agent == "translator":
            agent_config_path = Path(__file__).parent / "knowledge-bases" / "translator" / "config.json"
        else:
            # Unknown agent, return shared config
            return {"error": "agent not found"}
        
        # Load and merge agent config
        if agent_config_path and agent_config_path.exists():
            with open(agent_config_path, 'r', encoding='utf-8') as f:
                agent_config = json.load(f)
            merged_config = deep_merge(main_config, agent_config)
            return merged_config
        
        return {"error": "config not found"}
        
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
    question_id = str(uuid.uuid4())
    
    def generate():
        # Send question_id in first chunk
        yield f"data: {json.dumps({'question_id': question_id, 'chunk': ''})}\n\n"
        
        translated = ""
        for chunk in translate_text_stream(
            text=request.text,
            target_language=request.target_language,
            source_language=request.source_language
        ):
            translated += chunk
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        
        # Save translation to log
        save_question_response(
            question_id, 
            f"[TRANSLATION {request.source_language}→{request.target_language}] {request.text}",
            translated
        )

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
