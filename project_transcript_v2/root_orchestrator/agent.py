from google.adk import Agent
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import SendMessageRequest, MessageSendParams
import httpx
import asyncio
import logging
import uuid
from groq import AsyncGroq
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class ProxyCorpRoot:
    def __init__(self):
        self.groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.ear_client = None


    async def setup(self):
        """Initializes A2A connections to remote agents."""
        # Using long timeouts for AI processing
        self.http_client = httpx.AsyncClient(timeout=60) 
        
        ear_url = "http://127.0.0.1:10001"
        ear_resolver = A2ACardResolver(self.http_client, ear_url)

        max_retries = 6
        for i in range(max_retries):
            try:
                logger.info(f"⏳ Waiting for Remote Agents to boot (Attempt {i+1}/{max_retries})...")
                
                ear_card = await ear_resolver.get_agent_card()
                self.ear_client = A2AClient(self.http_client, ear_card, url=ear_url)
                
                logger.info("✅ Successfully connected to EAR and LINGUIST agents!")
                return # Exit the loop if successful
                
            except Exception as e:
                logger.warning(f"⚠️ EAR Agent not ready yet. Retrying in 3 seconds...")
                if i < max_retries - 1:
                    await asyncio.sleep(3)
                else:
                    raise e

    async def process_transcript(self, text: str):
        """
        This is the bridge! The Server calls this when the Ear outputs text.
        It asks the Linguist to analyze it.
        """
        if not self.groq_client: return

        logger.info(f"🧠 Orchestrator asking Linguist to analyze: '{text}'")
        
        try:
            # Direct ADK call! Returns the actual text immediately, bypassing A2A errors.
            response = await self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system", 
                        "content": "You monitor meeting transcripts for language shifts. "
                                   "If you detect Hindi/Gujarati/Hinglish, respond ONLY with: switch_to_hindi or switch_to_gujarati. "
                                   "If the language is clearly English, respond ONLY with: switch_to_english. "
                                   "Output commands only."
                    },
                    {"role": "user", "content": text}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.1 # Low temperature for strict command outputs
            )

            command = response.choices[0].message.content.strip().lower()
            
            if "switch_to" in command:
                logger.info(f"🔄 Orchestrator executing shift: {command}")
                await self.switch_ear_language(command)
        except Exception as e:
            logger.error(f"❌ Failed to parse Linguist response: {e}")

    async def switch_ear_language(self, command: str):
        """Root command to change Ear's transcription model."""
        target_lang = command.replace("switch_to_", "")
        msg_id = str(uuid.uuid4())
        
        payload = {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": f"update_language {target_lang}"}],
                "messageId": msg_id,
            }
        }
        
        request = SendMessageRequest(id=msg_id, params=MessageSendParams.model_validate(payload))
        await self.ear_client.send_message(request)
