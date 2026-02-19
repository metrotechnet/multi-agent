"""
TTS Routes - Text-to-Speech endpoint
"""
from fastapi import APIRouter, Body
from fastapi.responses import Response, JSONResponse
import openai
import os

router = APIRouter()


@router.post("/api/tts")
async def text_to_speech(
    text: str = Body(..., embed=True),
    language: str = Body("fr", embed=True)
):
    """
    Convert text to speech using OpenAI TTS API.
    Returns audio/mpeg stream.
    """
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
