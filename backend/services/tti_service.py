import logging
import urllib.parse
import httpx
from fastapi import HTTPException
import os
import uuid

from config.config import (
    POLLINATIONS_BASE_URL,
    IMAGE_DEFAULT_WIDTH,
    IMAGE_DEFAULT_HEIGHT,
)

logger = logging.getLogger(__name__)

# Pollinations query defaults
DEFAULT_SEED = 42
ENHANCE_PROMPT = True        # Let Pollinations enhance the prompt automatically
SAFE_FILTER = True           # Enable Pollinations safety filter
REQUEST_TIMEOUT = 90.0       # Seconds — image generation can be slow


def build_image_url(
    prompt: str,
    width: int = IMAGE_DEFAULT_WIDTH,
    height: int = IMAGE_DEFAULT_HEIGHT,
    seed: int = DEFAULT_SEED,
    enhance: bool = ENHANCE_PROMPT,
    safe: bool = SAFE_FILTER,
    model: str = "turbo",  # Using turbo for faster generation
) -> str:
    encoded_prompt = urllib.parse.quote(prompt, safe="")
    params = urllib.parse.urlencode(
        {
            "width": width,
            "height": height,
            "seed": seed,
            "enhance": str(enhance).lower(),
            "safe": str(safe).lower(),
            "model": model,
            "nologo": "true",
        }
    )
    url = f"{POLLINATIONS_BASE_URL}/{encoded_prompt}?{params}"
    logger.info("Built Pollinations URL: %s", url[:160])
    return url




# Setup output directory
import pathlib
BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def generate_image(
    prompt: str,
    width: int = IMAGE_DEFAULT_WIDTH,
    height: int = IMAGE_DEFAULT_HEIGHT,
) -> dict:
    prompt = prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Image prompt cannot be empty.")

    # 1. Build the external Pollinations URL
    external_url = build_image_url(prompt, width=width, height=height)
    
    # 2. Download the image to local storage
    # This avoids CORS/403 issues in the frontend
    local_filename = f"{uuid.uuid4()}.png"
    local_path = OUTPUT_DIR / local_filename
    
    logger.info("Downloading image from Pollinations for prompt: %r", prompt[:80])
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(external_url)
            if response.status_code != 200:
                logger.error("Pollinations returned %d", response.status_code)
                raise HTTPException(
                    status_code=502, 
                    detail=f"Image service (Pollinations) returned {response.status_code}"
                )
            
            with open(local_path, "wb") as f:
                f.write(response.content)
                
        # 3. Construct local URL (relative to backend)
        local_url = f"/outputs/{local_filename}"
        
        return {
            "image_url": local_url,
            "external_url": external_url, # Keep original for reference
            "prompt": prompt,
            "width": width,
            "height": height,
        }
    except Exception as e:
        logger.error("Failed to download image: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save generated image: {str(e)}")
