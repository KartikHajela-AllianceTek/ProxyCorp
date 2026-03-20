# ai_agent/main.py
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from a2a.server.agent_execution import AgentExecutor
from a2a.utils import new_agent_text_message
from icecream import ic
from groq import Groq
from dotenv import load_dotenv
import os
import asyncio
import httpx

load_dotenv()

from groq import Groq

API_KEY = os.getenv("API_KEY")

client = Groq(api_key=API_KEY)


def decide_dev(msg):
    prompt = f"""
        You are a tech lead.

        Decide which developer should handle this task:
        - ML_DEV → AI/ML tasks
        - BACKEND_DEV → APIs, backend systems
        - MOBILE_DEV → Android/iOS

        Respond ONLY with one word.

        Input: {msg}
        """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content.strip()


class AIExecutor(AgentExecutor):
    async def call_agent(self, url, msg):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "jsonrpc": "2.0",
                    "id": "1",
                    "method": "message/send",
                    "params": {
                        "message": {
                            "role": "user",
                            "parts": [{"kind": "text", "text": msg}],
                            "messageId": "1",
                        }
                    },
                },
            )

        data = response.json()

        if "result" not in data:
            return None, data

        text = data["result"]["parts"][0]["text"]
        return text, None

    async def execute(self, context, event_queue):
        part = context.message.parts[0]
        part_dict = part.model_dump()

        msg = part_dict.get("text") or part_dict.get("root", {}).get("text", "")
        msg = msg.lower()

        dev_answer = await asyncio.to_thread(decide_dev, msg)
        dev = dev_answer.strip().upper()

        # normalize
        if "ML" in dev:
            dev = "ML_DEV"
        elif "BACKEND" in dev:
            dev = "BACKEND_DEV"
        elif "MOBILE" in dev or "ANDROID" in dev:
            dev = "MOBILE_DEV"
        else:
            dev = "UNKNOWN"

        dev_map = {
            "ML_DEV": ("http://localhost:9006/", "ML Dev"),
            "BACKEND_DEV": ("http://localhost:9007/", "Backend Dev"),
            "MOBILE_DEV": ("http://localhost:9008/", "Mobile Dev"),
        }

        if dev not in dev_map:
            result = "TL: Could not determine developer"

        else:
            url, dev_name = dev_map[dev]

            dev_response, error = await self.call_agent(url, msg)

            if error:
                result = f"TL: Error from {dev_name} {error}"
            else:
                result = f"TL → {dev_response}"

        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(self, context, event_queue):
        raise Exception("cancel not supported")


skill = AgentSkill(
    id="ai",
    name="AI TL",
    description="Handles AI tasks",
    tags=["AI Agent"],
)


agent_card = AgentCard(
    name="AI Agent",
    description="AI team lead",
    url="http://localhost:9002",
    version="1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
)

handler = DefaultRequestHandler(
    agent_executor=AIExecutor(),
    task_store=InMemoryTaskStore(),
)

app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=handler,
)

if __name__ == "__main__":
    uvicorn.run(app.build(), port=9002)
