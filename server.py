import time
import asyncio
import json
import logging
import os
import base64
from dotenv import load_dotenv
from aiohttp import web

# Import our separated AI module
from ai_agent import TranscriberAgent

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

PORT = int(os.getenv("PORT", 3000))

# ── single global agent ──
agent = TranscriberAgent()

# ── /audio — Recall.ai raw audio input ──
async def handle_audio(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    logger.info("Audio WebSocket connected from Recall.ai")

    audio_msg_count = 0
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    event = json.loads(msg.data)
                    if event.get("event") == "audio_mixed_raw.data":
                        b64 = event["data"]["data"]["buffer"]
                        pcm_bytes = base64.b64decode(b64)
                        if pcm_bytes:
                            audio_msg_count += 1
                            if audio_msg_count <= 3 or audio_msg_count % 500 == 0:
                                logger.info(f"Recall.ai audio #{audio_msg_count}: {len(pcm_bytes)} bytes")
                            await agent.send_audio(pcm_bytes)
                except Exception as e:
                    logger.error(f"Audio processing error: {e}")

            elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.CLOSING, web.WSMsgType.CLOSED):
                logger.info("Recall.ai closing connection")
                break

    except Exception as e:
        logger.error(f"Audio WebSocket error: {e}")
    finally:
        logger.info(f"Audio WebSocket closed (processed {audio_msg_count} audio messages)")
        return ws

async def serve_avatar(request):
    return web.FileResponse(r'C:\Users\kartik.hajela\Documents\GitHub\ProxyCorp\index.html')

# ── Main ──
async def main():
    app = web.Application()
    app.router.add_get("/audio", handle_audio) # Only the audio route is needed now!
    app.router.add_get("/avatar", serve_avatar)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logger.info(f"Passive Scribe Server running on http://0.0.0.0:{PORT}")
    logger.info("  GET /audio  → Recall.ai raw audio input from meeting")

    asyncio.create_task(agent.run())
    logger.info("Deepgram + Groq agent started — waiting for audio stream")

    await asyncio.Future()

if __name__ == "__main__":
    time.sleep(10)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down")