# =====================================================
# Translation Agent - Module de traduction
# Utilise OpenAI Whisper pour audio et GPT pour texte
# =====================================================

import os
import tempfile
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / '.env')

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Supported translation languages
SUPPORTED_LANGUAGES = {
    "fr": "French",
    "en": "English",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "pl": "Polish",
    "tr": "Turkish",
    "sv": "Swedish",
    "da": "Danish",
    "no": "Norwegian",
    "fi": "Finnish",
    "uk": "Ukrainian",
    "cs": "Czech",
    "ro": "Romanian",
    "el": "Greek",
    "he": "Hebrew",
    "th": "Thai",
    "vi": "Vietnamese",
    "id": "Indonesian",
}


def translate_text_stream(text: str, target_language: str, source_language: str = "auto"):
    """
    Translate text to target language using GPT-4o-mini with streaming.
    Uses Whisper-style translation approach through the OpenAI API.

    Args:
        text: The text to translate
        target_language: Target language code (e.g., 'fr', 'en', 'es')
        source_language: Source language code or 'auto' for auto-detection

    Yields:
        str: Translated text chunks
    """
    target_lang_name = SUPPORTED_LANGUAGES.get(target_language, target_language)
    source_lang_name = SUPPORTED_LANGUAGES.get(source_language, "auto-detect")

    if source_language == "auto":
        source_instruction = "Auto-detect the source language."
    else:
        source_instruction = f"The source language is {source_lang_name}."

    system_prompt = (
        f"You are a professional translator. {source_instruction} "
        f"Translate the following text to {target_lang_name}. "
        f"Provide ONLY the translation, no explanations, no notes, no original text. "
        f"Maintain the original formatting, tone, and style. "
        f"If the text is already in {target_lang_name}, return it as-is."
    )

    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        stream=True,
        temperature=0.3,
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def transcribe_audio_whisper(audio_bytes: bytes, filename: str = "audio.webm", language: str = None) -> str:
    """
    Transcribe audio using OpenAI Whisper API.

    Args:
        audio_bytes: Raw audio bytes
        filename: Original filename for format detection
        language: Optional ISO-639-1 language code (e.g., 'en', 'fr') for better accuracy

    Returns:
        str: Transcribed text
    """
    suffix = Path(filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as audio_file:
            params = {
                "model": "whisper-1",
                "file": audio_file,
                "response_format": "text"
            }
            if language:
                params["language"] = language
            
            transcript = client.audio.transcriptions.create(**params)
        return transcript.strip()
    finally:
        os.unlink(tmp_path)


def translate_audio_whisper(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    Translate audio to English using OpenAI Whisper API translation endpoint.
    Whisper natively translates any language audio to English.

    Args:
        audio_bytes: Raw audio bytes
        filename: Original filename for format detection

    Returns:
        str: Translated English text
    """
    suffix = Path(filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as audio_file:
            translation = client.audio.translations.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return translation.strip()
    finally:
        os.unlink(tmp_path)


def get_supported_languages() -> dict:
    """Return the dictionary of supported languages."""
    return SUPPORTED_LANGUAGES
