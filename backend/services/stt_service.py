import os
import logging
import httpx
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("GROQ_API_KEY", "")
WHISPER_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

WHISPER_MODEL = "whisper-large-v3"

SUPPORTED_AUDIO_TYPES = {
    "audio/webm", "audio/mp4", "audio/mpeg", "audio/wav", "audio/ogg", 
    "audio/flac", "audio/x-m4a", "audio/mp3", "video/webm", "video/mpeg", "video/mp4"
}

SUPPORTED_EXTENSIONS = {
    ".webm", ".mp4", ".mpeg", ".wav", ".ogg", ".flac", ".mp3", ".m4a"
}



async def transcribe_audio(file: UploadFile) -> str:
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the server.",
        )

    content_type = file.content_type or ""
    filename = file.filename or ""
    extension = os.path.splitext(filename)[1].lower() if filename else ""

    # Accept if it's an audio MIME type OR has a supported extension
    is_valid = (content_type.startswith("audio/") or 
                content_type in SUPPORTED_AUDIO_TYPES or 
                extension in SUPPORTED_EXTENSIONS)

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{content_type or extension}'. Please upload a valid audio file.",
        )


    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

    # Map MIME types to extensions to help Whisper identify the format
    mime_to_ext = {
        "audio/webm": ".webm",
        "video/webm": ".webm",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/mp4": ".m4a",
        "video/mp4": ".mp4",
        "audio/x-m4a": ".m4a",
        "video/mpeg": ".mpeg",
    }
    
    content_type = file.content_type or "audio/webm"
    ext = mime_to_ext.get(content_type, ".webm")
    filename = f"recording{ext}"

    logger.info("Sending %d bytes of audio (%s, %s) to Whisper API", len(audio_bytes), filename, content_type)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                WHISPER_API_URL,
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                files={"file": (filename, audio_bytes, content_type)},
                data={"model": WHISPER_MODEL},
            )

        if response.status_code != 200:
            error_detail = response.text
            logger.error("Whisper API error %s: %s", response.status_code, error_detail)
            raise HTTPException(
                status_code=502,
                detail=f"Whisper API returned {response.status_code}: {error_detail}",
            )

        result = response.json()
        transcript = result.get("text", "").strip()

        if not transcript:
            raise HTTPException(
                status_code=422,
                detail="Whisper could not detect any speech in the audio.",
            )

        logger.info("Transcription successful: %r", transcript[:120])
        return transcript

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Whisper API request timed out. Please try again.",
        )
    except httpx.RequestError as exc:
        logger.exception("Network error calling Whisper API")
        raise HTTPException(
            status_code=502,
            detail=f"Network error contacting Whisper API: {exc}",
        )