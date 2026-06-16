"""
Audio Service — Remote API Client for Whisper (STT) + Kokoro TTS.

All models run on the Jupyter Cloud GPU environment.
This service is a thin HTTP client that sends requests to cloud endpoints.

NO models are loaded locally.
NO local inference.
NO GPU required on local machine.

Flow:
    STT:  audio_bytes → HTTP POST → Cloud Whisper → transcript
    TTS:  text → HTTP POST → Cloud Kokoro → audio_bytes
"""

import os
import io
import httpx
from pathlib import Path
from app.utils.logger import get_service_logger

logger = get_service_logger("audio_service")


class AudioService:
    """
    Thin HTTP client for remote Whisper (STT) and Kokoro (TTS) endpoints.
    All inference happens on the Jupyter Cloud GPU environment.
    """

    def __init__(self):
        self.whisper_url = os.getenv("WHISPER_API_URL", "http://localhost:8001")
        self.kokoro_url = os.getenv("KOKORO_API_URL", "http://localhost:8002")
        self.kokoro_voice = os.getenv("KOKORO_VOICE", "af_heart")
        self.kokoro_speed = float(os.getenv("KOKORO_SPEED", "1.0"))
        self._client = httpx.Client(timeout=120.0)
        self._async_client = httpx.AsyncClient(timeout=120.0)
        self.audio_dir = Path("app/static/audio")
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    # ── Whisper Large V3 (Speech-to-Text) ──────────────────────

    def transcribe_audio(self, audio_bytes: bytes, language: str = "en") -> str:
        """
        Transcribe candidate audio via remote Whisper Large V3 endpoint.
        
        Sends audio bytes to Cloud GPU, receives transcript text.
        
        Args:
            audio_bytes: WAV audio bytes from st.audio_input()
            language: Language code for transcription
            
        Returns:
            Transcribed text string
        """
        if not audio_bytes:
            return ""

        try:
            files = {"audio": ("recording.wav", io.BytesIO(audio_bytes), "audio/wav")}
            params = {"language": language}

            resp = self._client.post(
                f"{self.whisper_url}/transcribe",
                files=files,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            text = data.get("text", "")
            duration = data.get("duration", 0)
            logger.info(f"Whisper transcribed ({duration:.1f}s audio): {text[:80]}...")
            return text if text.strip() else "[No speech detected — please try again or type your answer]"

        except httpx.ConnectError:
            logger.error(f"Cannot connect to Whisper endpoint at {self.whisper_url}")
            return "[Whisper service unavailable — please type your answer]"
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return f"[Transcription error: {e}]"

    async def transcribe_audio_async(self, audio_bytes: bytes, language: str = "en") -> str:
        """Async version of transcribe_audio."""
        if not audio_bytes:
            return ""
        try:
            files = {"audio": ("recording.wav", io.BytesIO(audio_bytes), "audio/wav")}
            params = {"language": language}
            resp = await self._async_client.post(
                f"{self.whisper_url}/transcribe", files=files, params=params
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("text", "")
        except httpx.ConnectError:
            return "[Whisper service unavailable — please type your answer]"
        except Exception as e:
            return f"[Transcription error: {e}]"

    # ── Kokoro TTS (Text-to-Speech) ────────────────────────────

    async def generate_speech(self, text: str, question_id: str) -> str:
        """
        Generate spoken audio via remote Kokoro TTS endpoint.
        
        Sends text to Cloud GPU, receives WAV audio, saves locally.
        
        Args:
            text: Question text to speak
            question_id: Unique ID for file caching
            
        Returns:
            Path to saved WAV file, or empty string on failure
        """
        output_path = self.audio_dir / f"q_{question_id}.wav"
        if output_path.exists():
            return str(output_path)

        try:
            # Clean text for speech (remove markdown)
            clean_text = text.replace("*", "").replace("#", "").replace("`", "")

            payload = {
                "text": clean_text,
                "voice": self.kokoro_voice,
                "speed": self.kokoro_speed,
            }

            resp = await self._async_client.post(
                f"{self.kokoro_url}/synthesize",
                json=payload,
            )
            resp.raise_for_status()

            # Save WAV bytes to local file
            with open(output_path, "wb") as f:
                f.write(resp.content)

            logger.info(f"Kokoro TTS audio saved: {output_path}")
            return str(output_path)

        except httpx.ConnectError:
            logger.warning(f"Cannot connect to Kokoro TTS at {self.kokoro_url}")
            return ""
        except Exception as e:
            logger.error(f"Kokoro TTS error: {e}")
            return ""

    def generate_speech_sync(self, text: str, question_id: str) -> str:
        """Synchronous version of generate_speech."""
        output_path = self.audio_dir / f"q_{question_id}.wav"
        if output_path.exists():
            return str(output_path)
        try:
            clean_text = text.replace("*", "").replace("#", "").replace("`", "")
            payload = {
                "text": clean_text,
                "voice": self.kokoro_voice,
                "speed": self.kokoro_speed,
            }
            resp = self._client.post(f"{self.kokoro_url}/synthesize", json=payload)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return str(output_path)
        except Exception as e:
            logger.error(f"Kokoro TTS sync error: {e}")
            return ""

    # ── Status Check ───────────────────────────────────────────

    def get_model_status(self) -> dict:
        """Check health of remote Whisper and Kokoro endpoints."""
        whisper_status = "unknown"
        kokoro_status = "unknown"

        try:
            resp = self._client.get(f"{self.whisper_url}/health", timeout=5)
            whisper_status = "connected" if resp.status_code == 200 else "error"
        except httpx.ConnectError:
            whisper_status = "unreachable"
        except Exception:
            whisper_status = "error"

        try:
            resp = self._client.get(f"{self.kokoro_url}/health", timeout=5)
            kokoro_status = "connected" if resp.status_code == 200 else "error"
        except httpx.ConnectError:
            kokoro_status = "unreachable"
        except Exception:
            kokoro_status = "error"

        return {
            "whisper": whisper_status,
            "whisper_url": self.whisper_url,
            "kokoro": kokoro_status,
            "kokoro_url": self.kokoro_url,
        }


# ── Singleton ─────────────────────────────────────────────────

_audio_service = AudioService()


def get_audio_service() -> AudioService:
    return _audio_service
