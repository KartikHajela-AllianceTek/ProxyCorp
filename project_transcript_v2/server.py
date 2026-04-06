import time
import asyncio
import json
import logging
import os
import base64
from dotenv import load_dotenv
from aiohttp import web

from ear_agent.agent_executor import DualTranscriberAgent
from root_orchestrator.agent import ProxyCorpRoot

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()
PORT = int(os.getenv("PORT", 3000))

agent = DualTranscriberAgent()
orchestrator = ProxyCorpRoot()

async def handle_audio(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    logger.info("Audio WebSocket connected from Recall.ai")

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                event = json.loads(msg.data)
                if event.get("event") == "audio_mixed_raw.data":
                    b64 = event["data"]["data"]["buffer"]
                    pcm_bytes = base64.b64decode(b64)
                    if pcm_bytes:
                        await agent.send_audio(pcm_bytes)
    except Exception as e:
        logger.error(f"Audio WebSocket error: {e}")
    finally:
        logger.info("Audio WebSocket closed")
        return ws
    
async def serve_avatar(request):
    return web.FileResponse(r'C:\Users\kartik.hajela\Documents\GitHub\ProxyCorp\project_transcript_v2\client\index.html')

async def main():
    # 1. Start A2A connections
    await orchestrator.setup()
    
    # 2. Wire the Ear's output to the Orchestrator's input
    agent.on_transcript_callback = orchestrator.process_transcript

    app = web.Application()
    app.router.add_get("/audio", handle_audio)
    app.router.add_get("/avatar", serve_avatar) 

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logger.info(f"Scribe Server running on port {PORT}")
    
    # Start the VAD loop
    asyncio.create_task(agent.run())

    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())