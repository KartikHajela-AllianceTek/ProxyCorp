import asyncio
import os
import logging
import time
import struct
import math
from dotenv import load_dotenv

from deepgram import DeepgramClient
from deepgram.clients.live.v1.client import LiveOptions

logger = logging.getLogger(__name__)
load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

class TranscriberAgent:
    def __init__(self):
        self.deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        self.dg_connection = None 
        
        # ── VAD Gatekeeper Settings ──
        self.is_dg_connected = False
        self.last_spoken_time = 0
        self.cooldown_seconds = 20
        self.noise_threshold_rms = 500  
        self._input_chunk_count = 0
        self._loop = None

    def _calculate_rms(self, pcm_bytes: bytes) -> float:
        count = len(pcm_bytes) // 2
        if count == 0: return 0.0
        try:
            shorts = struct.unpack(f'<{count}h', pcm_bytes)
            sum_squares = sum(s * s for s in shorts)
            return math.sqrt(sum_squares / count)
        except:
            return 0.0

    async def run(self):
        self._loop = asyncio.get_running_loop()
        logger.info("🛡️ VAD Gatekeeper active. Monitoring stream...")
        while True:
            await asyncio.sleep(1)

    def _start_deepgram(self):
        if self.is_dg_connected: return

        logger.info("🔊 Volume spike detected! Waking up Deepgram...")
        self.dg_connection = self.deepgram.listen.live.v("1")

        def on_message(self_obj, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript if result.channel.alternatives else ""
            if sentence.strip():
                # NO MORE GROQ! Just pure transcription output.
                logger.info(f"🗣️ Transcript: {sentence}")

        def on_error(self_obj, error, **kwargs):
            logger.error(f"❌ Deepgram Error: {error}")

        self.dg_connection.on("Results", on_message)
        self.dg_connection.on("Error", on_error)

        options = LiveOptions(model="nova-3", language="en-US", encoding="linear16", channels=1, sample_rate=16000)
        
        if self.dg_connection.start(options):
            self.is_dg_connected = True

    def _stop_deepgram(self):
        if not self.is_dg_connected: return
        logger.info("⏰ Cooldown reached. Putting Deepgram to sleep.")
        self.dg_connection.finish()
        self.is_dg_connected = False
        self.dg_connection = None

    async def send_audio(self, pcm_bytes: bytes):
        self._input_chunk_count += 1
        current_time = time.time()
        rms_volume = self._calculate_rms(pcm_bytes)

        if rms_volume > self.noise_threshold_rms:
            self.last_spoken_time = current_time
            if not self.is_dg_connected: self._start_deepgram()

        if self.is_dg_connected:
            self.dg_connection.send(pcm_bytes)
            if current_time - self.last_spoken_time > self.cooldown_seconds:
                self._stop_deepgram()