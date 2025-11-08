# utils/voice.py
"""Voice input/output utilities for Casa Amigo chatbot."""

import tempfile
from pathlib import Path
from typing import Optional, BinaryIO
import openai


class VoiceManager:
    """Manages speech-to-text and text-to-speech operations."""
    
    def __init__(self, api_key: str):
        """
        Initialize VoiceManager with OpenAI API key.
        
        Args:
            api_key: OpenAI API key for Whisper and TTS
        """
        self.client = openai.OpenAI(api_key=api_key)
    
    def transcribe_audio(self, audio_data, language: str = "en") -> Optional[str]:
        """
        Transcribe audio using OpenAI Whisper API.
        
        Args:
            audio_data: AudioSegment object or raw audio bytes in WAV format
            language: Language code (e.g., "en", "zh", "ms") or None for auto-detect
        
        Returns:
            Transcribed text or None if transcription failed
        """
        tmp_path = None
        try:
            # Handle AudioSegment object from streamlit-audiorecorder
            from pydub import AudioSegment
            
            if isinstance(audio_data, AudioSegment):
                # Export AudioSegment to temporary WAV file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                    audio_data.export(tmp_file.name, format="wav")
                    tmp_path = tmp_file.name
            else:
                # Handle raw bytes
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                    tmp_file.write(audio_data)
                    tmp_path = tmp_file.name
            
            print(f"[VOICE] Transcribing audio file: {tmp_path}")
            
            # Transcribe using Whisper
            with open(tmp_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language if language else None  # None = auto-detect
                )
            
            text = transcript.text.strip()
            print(f"[VOICE] Transcription successful: {text[:100]}...")
            return text
        
        except Exception as e:
            print(f"[VOICE] Transcription error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        finally:
            # Always cleanup temp file
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception as cleanup_error:
                    print(f"[VOICE] Cleanup error: {cleanup_error}")
    
    def text_to_speech(
        self, 
        text: str, 
        voice: str = "nova",
        model: str = "tts-1"
    ) -> Optional[bytes]:
        """
        Convert text to speech using OpenAI TTS API.
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: TTS model ("tts-1" or "tts-1-hd")
        
        Returns:
            Audio bytes (MP3 format) or None if generation failed
        """
        try:
            # TTS has a 4096 character limit
            if len(text) > 4096:
                print(f"[VOICE] Text too long ({len(text)} chars), truncating to 4096")
                text = text[:4096]
            
            print(f"[VOICE] Generating speech: {len(text)} chars, voice={voice}")
            
            # Generate speech
            response = self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text
            )
            
            # Return audio bytes directly (no temp file needed)
            audio_bytes = response.content
            print(f"[VOICE] Speech generated: {len(audio_bytes)} bytes")
            return audio_bytes
        
        except Exception as e:
            print(f"[VOICE] TTS error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def get_supported_voices() -> list[str]:
        """Get list of supported TTS voices."""
        return ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    
    @staticmethod
    def get_supported_languages() -> dict[str, str]:
        """Get dictionary of supported Whisper languages."""
        return {
            "en": "English",
            "zh": "Chinese",
            "ms": "Malay",
            "ta": "Tamil",
            "auto": "Auto-detect"
        }