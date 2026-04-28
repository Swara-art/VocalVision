import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from models.model import VocalVisionResponse
from services.stt_service import transcribe_audio
from services.translate_service import detect_and_translate
from services.tti_service import generate_image
from config.config import IMAGE_DEFAULT_WIDTH, IMAGE_DEFAULT_HEIGHT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["VocalVision Orchestrator"])

@router.post(
    "/speech-to-image",
    response_model=VocalVisionResponse,
    summary="Combined endpoint: Transcribe audio, translate if needed, AND generate image",
    description=(
        "Orchestrates the full pipeline:\n"
        "1. Transcribes uploaded audio using Whisper (supports 90+ languages)\n"
        "2. Detects the language of the transcript\n"
        "3. Translates to English if it's not already English\n"
        "4. Generates an image from the English prompt via Pollinations.ai"
    ),
)
async def speech_to_image_endpoint(
    audio: UploadFile = File(..., description="Audio file to transcribe and visualize"),
):
    logger.info("Received combined request: %s", audio.filename)

    # ── Step 1: Transcribe ──────────────────────────────────────────────────
    try:
        transcript = await transcribe_audio(audio)
        logger.info("Transcript: %r", transcript[:120])
    except Exception as e:
        logger.error("Transcription failed in orchestrator: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    # ── Step 2: Detect language & translate if needed ───────────────────────
    try:
        translation_result = await detect_and_translate(transcript)
        english_prompt = translation_result["translated_text"]
        detected_language = translation_result["detected_language"]
        was_translated = translation_result["was_translated"]

        if was_translated:
            logger.info(
                "Translation applied [%s → English]: %r → %r",
                detected_language,
                transcript[:80],
                english_prompt[:80],
            )
        else:
            logger.info("No translation needed — language: %s", detected_language)

    except Exception as e:
        # Non-fatal: if translation service fails, fall back to raw transcript
        logger.error("Translation step failed (falling back to raw transcript): %s", e)
        english_prompt = transcript
        detected_language = "Unknown"
        was_translated = False

    # ── Step 3: Generate image from English prompt ──────────────────────────
    try:
        image_data = await generate_image(
            prompt=english_prompt,
            width=IMAGE_DEFAULT_WIDTH,
            height=IMAGE_DEFAULT_HEIGHT,
        )
    except Exception as e:
        logger.error("Image generation failed in orchestrator: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    # ── Step 4: Return combined response ────────────────────────────────────
    return VocalVisionResponse(
        image_url=image_data["image_url"],
        transcription=transcript,          # original transcript (in source language)
        translated_prompt=english_prompt,  # what was actually sent to image gen
        detected_language=detected_language,
        was_translated=was_translated,
        width=image_data["width"],
        height=image_data["height"],
    )