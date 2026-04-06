import os
import requests
import io
import wave
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def get_deepgram_config() -> Dict[str, Any]:
    """Configures Deepgram Nova-3 for English."""
    return {
        "model": "nova-3",
        "language": "en-US",
        "smart_format": True,
        "diarize": True, 
        "interim_results": True,
        "encoding": "linear16",
        "sample_rate": 16000,
        "channels": 1
    }

def create_wav_buffer(pcm_bytes: bytes, sample_rate: int = 16000) -> io.BytesIO:
    """Wraps raw PCM bytes into a valid WAV file in memory for Sarvam AI."""
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2) # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    wav_io.seek(0)
    return wav_io

def transcribe_with_sarvam(pcm_bytes: bytes, language_code: str) -> str:
    """
    Sends buffered audio to Sarvam's speech-to-text API.
    language_code: 'hi-IN' for Hindi, 'gu-IN' for Gujarati.
    """
    sarvam_api_key = os.getenv("SARVAM_API_KEY")
    if not sarvam_api_key:
        logger.error("Missing SARVAM_API_KEY")
        return ""

    # Sarvam's STT endpoint (refer to their latest docs for exact URL)
    url = "https://api.sarvam.ai/speech-to-text-translate" 
    
    wav_buffer = create_wav_buffer(pcm_bytes)
    
    headers = {"api-subscription-key": sarvam_api_key}
    files = {'file': ('audio.wav', wav_buffer, 'audio/wav')}
    data = {'prompt': 'Transcribe accurately in Latin script if possible.'}
    
    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        if response.status_code == 200:
            return response.json().get("transcript", "")
        else:
            logger.error(f"Sarvam API Error: {response.text}")
            return ""
    except Exception as e:
        logger.error(f"Failed to reach Sarvam: {e}")
        return ""