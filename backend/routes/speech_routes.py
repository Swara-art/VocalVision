import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from models.model import TranscriptionResponse


from services.stt_service import transcribe_audio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Speech-to-Text"])


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    summary="Convert speech audio to text via OpenAI Whisper",
    description=(
        "Upload an audio file (webm, mp4, wav, mp3, ogg, flac) and receive "
        "the transcribed text back. The transcription is performed by the "
        "OpenAI Whisper API (`whisper-1` model)."
    ),
)
async def transcribe_endpoint(
    file: UploadFile = File(
        ...,
        description="Audio file recorded from the browser microphone.",
    ),
):
    logger.info(
        "Received transcription request — filename=%s content_type=%s",
        file.filename,
        file.content_type,
    )

    if not file.filename and not file.content_type:
        raise HTTPException(status_code=400, detail="No audio file received.")

    transcript = await transcribe_audio(file)

    return TranscriptionResponse(
        transcript=transcript,
        char_count=len(transcript),
    )