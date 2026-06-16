"""
AI Interviewer – Cloud Model Server

FastAPI server that wraps Whisper Large V3, Kokoro TTS, and BGE-M3.
Runs on Jupyter Cloud GPU environment alongside vLLM (DeepSeek-R1).

IMPORTANT: Uses HuggingFace Transformers pipeline for Whisper (ROCm compatible).
           Does NOT use faster_whisper/ctranslate2 (NVIDIA CUDA only).

Endpoints:
    POST /transcribe     — Whisper Large V3 (audio → text)
    POST /synthesize     — Kokoro TTS (text → audio)
    POST /embed          — BGE-M3 (text → embedding vectors)
    GET  /health         — Health check for all models
    GET  /status         — Detailed model status

Usage:
    uvicorn model_server:app --host 0.0.0.0 --port 8001
"""

import io
import os
import time
import tempfile
import numpy as np
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="AI Interviewer – Cloud Model Server",
    description="Whisper V3 + Kokoro TTS + BGE-M3 on GPU (ROCm compatible)",
    version="1.0.0",
)

# ── Global Model Holders ─────────────────────────────────────

_whisper_pipe = None
_kokoro_pipeline = None
_embedding_model = None


# ══════════════════════════════════════════════════════════════
# WHISPER LARGE V3 — Speech-to-Text (using transformers pipeline)
# ══════════════════════════════════════════════════════════════

def get_whisper():
    """Lazy-load Whisper Large V3 using HuggingFace Transformers pipeline.
    
    Uses transformers + PyTorch (ROCm compatible).
    Does NOT use faster_whisper/ctranslate2 (NVIDIA only).
    """
    global _whisper_pipe
    if _whisper_pipe is not None:
        return _whisper_pipe
    
    import torch
    from transformers import pipeline
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    
    print(f"[Whisper] Loading openai/whisper-large-v3 on {device} ({dtype})...")
    _whisper_pipe = pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-large-v3",
        torch_dtype=dtype,
        device=device,
    )
    print("[Whisper] Model loaded successfully!")
    return _whisper_pipe


@app.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Query("en"),
):
    """Transcribe audio using Whisper Large V3 (transformers pipeline)."""
    start = time.time()
    
    # Save uploaded audio to temp file
    content = await audio.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        pipe = get_whisper()
        
        result = pipe(
            tmp_path,
            generate_kwargs={"language": language},
            return_timestamps=True,
        )
        
        text = result.get("text", "").strip()
        elapsed = time.time() - start

        return {
            "text": text,
            "language": language,
            "language_probability": 1.0,
            "duration": round(elapsed, 2),
            "processing_time": round(elapsed, 2),
            "model": "openai/whisper-large-v3",
        }
    finally:
        os.unlink(tmp_path)


# ══════════════════════════════════════════════════════════════
# KOKORO TTS — Text-to-Speech
# ══════════════════════════════════════════════════════════════

class TTSRequest(BaseModel):
    text: str
    voice: str = "af_heart"
    speed: float = 1.0


def get_kokoro():
    """Lazy-load Kokoro TTS pipeline."""
    global _kokoro_pipeline
    if _kokoro_pipeline is not None:
        return _kokoro_pipeline
    from kokoro import KPipeline
    print("[Kokoro] Loading TTS pipeline (American English)...")
    _kokoro_pipeline = KPipeline(lang_code='a')
    print("[Kokoro] Pipeline loaded successfully!")
    return _kokoro_pipeline


@app.post("/synthesize")
async def synthesize_speech(request: TTSRequest):
    """Generate speech audio using Kokoro TTS."""
    start = time.time()
    pipeline = get_kokoro()

    # Generate audio
    audio_segments = []
    generator = pipeline(request.text, voice=request.voice, speed=request.speed)
    for _, _, audio in generator:
        audio_segments.append(audio)

    if not audio_segments:
        return JSONResponse(
            status_code=500,
            content={"error": "No audio generated"},
        )

    full_audio = np.concatenate(audio_segments)
    elapsed = time.time() - start

    # Encode as WAV
    import soundfile as sf
    buffer = io.BytesIO()
    sf.write(buffer, full_audio, samplerate=24000, format="WAV")
    buffer.seek(0)

    return Response(
        content=buffer.getvalue(),
        media_type="audio/wav",
        headers={
            "X-Processing-Time": str(round(elapsed, 2)),
            "X-Model": "hexgrad/Kokoro-82M",
            "X-Voice": request.voice,
        },
    )


# ══════════════════════════════════════════════════════════════
# BGE-M3 — Embeddings
# ══════════════════════════════════════════════════════════════

class EmbedRequest(BaseModel):
    texts: list[str]


def get_embedding_model():
    """Lazy-load BGE-M3 on GPU."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    from sentence_transformers import SentenceTransformer
    print(f"[BGE-M3] Loading BAAI/bge-m3 on {device}...")
    _embedding_model = SentenceTransformer("BAAI/bge-m3", device=device)
    print("[BGE-M3] Model loaded successfully!")
    return _embedding_model


@app.post("/embed")
async def generate_embeddings(request: EmbedRequest):
    """Generate embeddings using BGE-M3."""
    start = time.time()
    model = get_embedding_model()

    embeddings = model.encode(
        request.texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    elapsed = time.time() - start

    return {
        "embeddings": embeddings.tolist(),
        "dimension": embeddings.shape[1],
        "count": len(request.texts),
        "processing_time": round(elapsed, 3),
        "model": "BAAI/bge-m3",
    }


# ══════════════════════════════════════════════════════════════
# Health & Status Endpoints
# ══════════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    """Quick health check — returns 200 if server is running."""
    return {"status": "healthy", "server": "ai-interviewer-model-server"}


@app.get("/status")
async def detailed_status():
    """Detailed status of all loaded models."""
    import torch
    device = "cuda (ROCm)" if torch.cuda.is_available() else "cpu"
    return {
        "whisper": {
            "loaded": _whisper_pipe is not None,
            "model": "openai/whisper-large-v3",
            "backend": "transformers (ROCm compatible)",
            "device": device,
        },
        "kokoro": {
            "loaded": _kokoro_pipeline is not None,
            "model": "hexgrad/Kokoro-82M",
        },
        "bge_m3": {
            "loaded": _embedding_model is not None,
            "model": "BAAI/bge-m3",
            "device": device,
        },
    }


@app.on_event("startup")
async def startup_preload():
    """Optionally preload models on startup for faster first request."""
    preload = os.getenv("PRELOAD_MODELS", "false").lower() == "true"
    if preload:
        print("[Startup] Preloading all models...")
        get_whisper()
        get_kokoro()
        get_embedding_model()
        print("[Startup] All models preloaded!")
    else:
        print("[Startup] Models will be loaded on first request (lazy loading)")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MODEL_SERVER_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
