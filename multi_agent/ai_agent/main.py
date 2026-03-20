# ai_agent/main.py  (AI TL — port 9002)

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
import asyncio

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from a2a.server.agent_execution import AgentExecutor
from a2a.utils import new_agent_text_message
from groq import Groq
from dotenv import load_dotenv

from utils import call_agent, extract_msg

load_dotenv()

client = Groq(api_key=os.getenv("API_KEY"))

TL_SLOTS = "2pm, 3pm"

DEV_MAP = {
    "ML_DEV": ("http://localhost:9006/", "ML Dev"),
    "BACKEND_DEV": ("http://localhost:9007/", "Backend Dev"),
    "MOBILE_DEV": ("http://localhost:9008/", "Mobile Dev"),
}


def decide_dev(msg: str) -> str:
    prompt = f"""You are an AI tech lead assigning developer tasks.

Choose the best developer:
- ML_DEV      → AI/ML features, models, recommendations, NLP
- BACKEND_DEV → APIs, databases, backend services, server logic
- MOBILE_DEV  → Android/iOS/mobile features

Respond ONLY with one word: ML_DEV or BACKEND_DEV or MOBILE_DEV

Input: {msg}"""
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip().upper()


def normalize_dev(raw: str) -> str:
    if "ML" in raw or "MACHINE" in raw:
        return "ML_DEV"
    if "BACKEND" in raw or "API" in raw or "SERVER" in raw:
        return "BACKEND_DEV"
    if "MOBILE" in raw or "ANDROID" in raw or "IOS" in raw:
        return "MOBILE_DEV"
    return "UNKNOWN"


class AITLExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        raw_msg = extract_msg(context)

        if "[INTENT:PROJECT]" in raw_msg:
            await event_queue.enqueue_event(new_agent_text_message(TL_SLOTS))
            return

        msg = raw_msg.replace("[INTENT:FEATURE]", "").strip().lower()

        dev_raw = await asyncio.to_thread(decide_dev, msg)
        dev = normalize_dev(dev_raw)

        if dev not in DEV_MAP:
            await event_queue.enqueue_event(
                new_agent_text_message("AI TL: Could not determine developer")
            )
            return

        dev_url, dev_name = DEV_MAP[dev]
        dev_response, error = await call_agent(dev_url, msg)

        if error:
            result = f"AI TL: Error from {dev_name} — {error}"
        else:
            result = f"AI TL → {dev_response}"

        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(self, context, event_queue):
        raise Exception("cancel not supported")


skill = AgentSkill(
    id="ai_tl",
    name="AI Tech Lead",
    description="Routes AI tasks to the right developer",
    tags=["AI TL"],
)

agent_card = AgentCard(
    name="AI TL Agent",
    description="AI team lead — delegates features to ML/Backend/Mobile devs",
    url="http://localhost:9002/",
    version="1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
)

handler = DefaultRequestHandler(
    agent_executor=AITLExecutor(),
    task_store=InMemoryTaskStore(),
)

app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler)

if __name__ == "__main__":
    uvicorn.run(app.build(), port=9002)
