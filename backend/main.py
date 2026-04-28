from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from routes.speech_routes import router as speech_routes
from routes.image_routes import router as image_routes
from routes.orchestrator_routes import router as orchestrator_routes
import os

app = FastAPI(
    title="VocalVision — Speech to Image API",
    description="Convert speech to stunning AI images using Web Speech API + Pollinations.ai",
    version="2.0.0",
)

# CORS — allow_credentials=False with wildcard origin (spec-compliant)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(speech_routes)
app.include_router(image_routes)
app.include_router(orchestrator_routes)


# Serve generated images (must be mounted before the root mount)
import pathlib
backend_dir = pathlib.Path(__file__).resolve().parent
outputs_path = backend_dir / "outputs"
outputs_path.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(outputs_path)), name="outputs")

# Serve the frontend as static files at root
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")