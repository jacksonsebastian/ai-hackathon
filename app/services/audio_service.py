"""
Audio Service for handling Text-to-Speech (AI Voice) and Speech-to-Text (Candidate Answer).
Uses edge-tts for high-quality, free AI voices.
Uses SpeechRecognition for transcribing candidate audio.
"""

import os
import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile
import speech_recognition as sr
from app.utils.logger import get_service_logger

logger = get_service_logger("audio_service")

class AudioService:
    def __init__(self):
        self.voice = "en-US-ChristopherNeural"  # Professional male AI voice
        # Ensure audio temp dir exists
        self.audio_dir = Path("app/static/audio")
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.recognizer = sr.Recognizer()

    async def generate_speech(self, text: str, question_id: str) -> str:
        """
        Generate MP3 audio from text using edge-tts.
        Returns the path to the generated MP3 file.
        """
        try:
            import edge_tts
        except ImportError:
            logger.error("edge-tts not installed. Cannot generate audio.")
            return ""

        # Clean text for speech (remove markdown)
        clean_text = text.replace("*", "").replace("#", "")
        
        output_path = self.audio_dir / f"q_{question_id}.mp3"
        if output_path.exists():
            return str(output_path)

        try:
            communicate = edge_tts.Communicate(clean_text, self.voice)
            await communicate.save(str(output_path))
            logger.info(f"Generated speech for question {question_id} at {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to generate speech: {e}")
            return ""

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio bytes (from st.audio_input) to text using SpeechRecognition.
        """
        if not audio_bytes:
            return ""

        try:
            # st.audio_input returns a WAV buffer, so we can use it directly
            with NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
                temp_wav.write(audio_bytes)
                temp_wav.flush()
                
                with sr.AudioFile(temp_wav.name) as source:
                    audio_data = self.recognizer.record(source)
                    text = self.recognizer.recognize_google(audio_data)
                    logger.info(f"Successfully transcribed audio: {text}")
                    
            os.unlink(temp_wav.name)
            return text
        except sr.UnknownValueError:
            logger.warning("Google Speech Recognition could not understand audio")
            return "Could not understand audio. Please type your answer or try speaking clearer."
        except sr.RequestError as e:
            logger.error(f"Could not request results from Google Speech Recognition service; {e}")
            return "Transcription service unavailable."
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            return "Error transcribing audio."

# Singleton instance
_audio_service = AudioService()

def get_audio_service() -> AudioService:
    return _audio_service
