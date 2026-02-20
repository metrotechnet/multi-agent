from instagrapi import Client
from moviepy.editor import VideoFileClip
from openai import OpenAI
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import json
import os
from tqdm import tqdm
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / '.env')



# Extract config values from environment variables
INSTAGRAM_USER = os.getenv("INSTAGRAM_USER", "")
INSTAGRAM_PASS = os.getenv("INSTAGRAM_PASSWORD", "")
TARGET_ACCOUNT = os.getenv("INSTAGRAM_TARGET_ACCOUNT", "")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

VIDEO_DIR = str(PROJECT_ROOT / "chroma_db" / "videos")
TRANSCRIPTS_DIR = str(PROJECT_ROOT / "transcripts")
CHROMA_DB_DIR = str(PROJECT_ROOT / "chroma_db")


# Setup folders
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
os.makedirs(CHROMA_DB_DIR, exist_ok=True)

# Clients
client_openai = OpenAI(api_key=OPENAI_API_KEY)

ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY, model_name="text-embedding-3-large"
)
chroma_client = chromadb.PersistentClient(
    path=CHROMA_DB_DIR,
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=False
    )
)
collection = chroma_client.get_or_create_collection(
    name="instagram_transcripts", embedding_function=ef
)

# Instagram login with fallback
cl = Client()
instagram_logged_in = False

def login_instagram():
    global instagram_logged_in
    try:
        print(f"Attempting Instagram login for user: {INSTAGRAM_USER}")
        cl.login(INSTAGRAM_USER, INSTAGRAM_PASS)
        instagram_logged_in = True
        print("✅ Instagram login successful")
        return True
    except Exception as e:
        print(f"❌ Instagram login failed: {str(e)}")
        print("⚠️  Instagram functionality will be disabled")
        instagram_logged_in = False
        return False

# Try to login at startup
login_instagram()

def run_pipeline(limit=10):
    if not instagram_logged_in:
        print("❌ Cannot run pipeline: Instagram login required but failed")
        print("📋 Available options:")
        print("  1. Check Instagram credentials in .env file")
        print("  2. Try calling retry_instagram_login() to retry authentication")
        print("  3. Use manual video processing mode")
        return {"error": "Instagram authentication required", "logged_in": False}
    
    try:
        medias = cl.user_medias(cl.user_id_from_username(TARGET_ACCOUNT), limit)
    except Exception as e:
        print(f"❌ Failed to fetch Instagram media: {str(e)}")
        print("🔄 Attempting to re-login...")
        if login_instagram():
            try:
                medias = cl.user_medias(cl.user_id_from_username(TARGET_ACCOUNT), limit)
            except Exception as retry_e:
                return {"error": f"Failed to fetch media after retry: {str(retry_e)}", "logged_in": instagram_logged_in}
        else:
            return {"error": "Authentication failed on retry", "logged_in": False}

    for m in tqdm(medias, desc="Processing videos"):
        if m.media_type != 2:  # vidéo
            continue

        video_path = cl.video_download(m.pk, VIDEO_DIR)
        audio_path = video_path.replace(".mp4", ".mp3")
        transcript_path = os.path.join(TRANSCRIPTS_DIR, os.path.basename(video_path).replace(".mp4", ".txt"))

        clip = VideoFileClip(video_path)
        clip.audio.write_audiofile(audio_path, logger=None)

        with open(audio_path, "rb") as f:
            transcript = client_openai.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=f
            )

        text = transcript.text
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(text)

        # Chunk & push to Chroma
        chunk_size = 500
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        for i, chunk in enumerate(chunks):
            collection.add(
                documents=[chunk],
                metadatas=[{"source": os.path.basename(video_path), "chunk": i}],
                ids=[f"{m.pk}_chunk_{i}"]
            )

    chroma_client.persist()
    print("✅ Pipeline terminé")

def retry_instagram_login():
    """Retry Instagram login - useful for manual authentication attempts"""
    return login_instagram()

def get_instagram_status():
    """Get current Instagram authentication status"""
    return {
        "logged_in": instagram_logged_in,
        "user": INSTAGRAM_USER if instagram_logged_in else "Not authenticated",
        "target_account": TARGET_ACCOUNT if instagram_logged_in else "N/A"
    }
