import logging
from fastapi import APIRouter
from models.model import ImageGenerationRequest, ImageGenerationResponse


from services.tti_service import generate_image
from config.config import IMAGE_DEFAULT_WIDTH, IMAGE_DEFAULT_HEIGHT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Text-to-Image"])

# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/generate-image",
    response_model=ImageGenerationResponse,
    summary="Generate an image from a text prompt via Pollinations.ai",
    description=(
        "Accepts a text prompt (typically the output of the /api/transcribe "
        "endpoint) and returns a direct Pollinations.ai image URL. "
        "No API key is required — Pollinations.ai is free and open."
    ),
)
async def generate_image_endpoint(body: ImageGenerationRequest):
    logger.info(
        "Image generation request — prompt=%r width=%d height=%d",
        body.prompt[:80],
        body.width,
        body.height,
    )

    result = await generate_image(
        prompt=body.prompt,
        width=body.width,
        height=body.height,
    )

    return ImageGenerationResponse(**result)