import pathlib
import logging
from dotenv import load_dotenv
import os

# Resolve .env relative to the project root (two levels up from this file)
_env_path = pathlib.Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_env_path)

# Pollinations.ai — free, no API key required
POLLINATIONS_BASE_URL = "https://image.pollinations.ai/prompt"

# Default Image Generation Settings
IMAGE_DEFAULT_WIDTH = 1024
IMAGE_DEFAULT_HEIGHT = 1024

logger = logging.getLogger(__name__)
logger.info("Using Pollinations.ai for image generation (no API key required)")
