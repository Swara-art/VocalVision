from pydantic import BaseModel, Field
from config.config import IMAGE_DEFAULT_WIDTH, IMAGE_DEFAULT_HEIGHT

class TranscriptionResponse(BaseModel):
    transcript: str
    char_count: int


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Text description of the image to generate.",
        examples=["a majestic snow leopard on a mountain at sunset"],
    )
    width: int = Field(
        default=IMAGE_DEFAULT_WIDTH,
        ge=256,
        le=2048,
        description="Output image width in pixels.",
    )
    height: int = Field(
        default=IMAGE_DEFAULT_HEIGHT,
        ge=256,
        le=2048,
        description="Output image height in pixels.",
    )

class ImageGenerationResponse(BaseModel):
    image_url: str
    prompt: str
    width: int
    height: int


class VocalVisionResponse(BaseModel):
    image_url: str
    transcription: str
    width: int
    height: int
    status: str = "success"