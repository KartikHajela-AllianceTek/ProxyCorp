# pm_agent/main.py

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
import asyncio

from a2a.server.apps import A2AStarletteApplication
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from a2a.server.agent_execution import AgentExecutor
from a2a.utils import new_agent_text_message
from groq import Groq
from dotenv import load_dotenv

from utils import call_agent, extract_msg

load_dotenv()

client = Groq(api_key=os.getenv("API_KEY"))

PM_CALENDAR = ["3pm", "4pm"]

TL_MAP = {
    "AI": ("http://localhost:9002/", "AI TL"),
    "ANDROID": ("http://localhost:9003/", "Android TL"),
}


def decide_intent(msg: str) -> str:
    prompt = f"""You are a project manager classifier.

Classify the request into ONE of:
- PROJECT  → new project, planning, discussion, kickoff
- FEATURE  → feature addition, bug fix, implementation, task

Respond ONLY with one word: PROJECT or FEATURE

Input: {msg}"""
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip().upper()


def decide_domain(msg: str) -> str:
    prompt = f"""You are a project manager.

Decide which team owns this request:
- AI      → machine learning, AI, recommendation, model, NLP
- ANDROID → mobile, android, app, iOS, flutter

Respond ONLY with one word: AI or ANDROID

Input: {msg}"""
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip().upper()


def normalize_intent(raw: str) -> str:
    if "PROJECT" in raw:
        return "PROJECT"
    if "FEATURE" in raw:
        return "FEATURE"
    return "UNKNOWN"


def normalize_domain(raw: str) -> str:
    if "ANDROID" in raw or "MOBILE" in raw:
        return "ANDROID"
    if "AI" in raw or "ML" in raw or "MACHINE" in raw:
        return "AI"
    return "UNKNOWN"


def find_common_slot(pm_slots: list[str], tl_slots: list[str]) -> str | None:
    tl_set = {s.strip().lower() for s in tl_slots}
    for slot in pm_slots:
        if slot.strip().lower() in tl_set:
            return slot
    return None


class PMExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        msg = extract_msg(context).lower()

        intent_raw, domain_raw = await asyncio.gather(
            asyncio.to_thread(decide_intent, msg),
            asyncio.to_thread(decide_domain, msg),
        )

        intent = normalize_intent(intent_raw)
        domain = normalize_domain(domain_raw)

        if domain not in TL_MAP:
            await event_queue.enqueue_event(
                new_agent_text_message("PM: Could not determine team domain")
            )
            return

        tl_url, tl_name = TL_MAP[domain]

        if intent == "PROJECT":
            tl_response, error = await call_agent(tl_url, f"[INTENT:PROJECT] {msg}")
            if error:
                result = f"PM: Error contacting {tl_name} — {error}"
            else:
                tl_slots = [s.strip() for s in tl_response.split(",")]
                common = find_common_slot(PM_CALENDAR, tl_slots)
                if common:
                    result = f"PM: Meeting scheduled with {tl_name} at {common}"
                else:
                    result = f"PM: No common slot with {tl_name} (PM: {PM_CALENDAR}, TL: {tl_slots})"

        elif intent == "FEATURE":
            tl_response, error = await call_agent(tl_url, f"[INTENT:FEATURE] {msg}")
            if error:
                result = f"PM: Error contacting {tl_name} — {error}"
            else:
                result = f"PM → {tl_response}"

        else:
            result = "PM: Could not determine intent (expected PROJECT or FEATURE)"

        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(self, context, event_queue):
        raise Exception("cancel not supported")


skill = AgentSkill(
    id="pm",
    name="Project Manager",
    description="Handles scheduling and feature delegation",
    tags=["PM Agent"],
)

agent_card = AgentCard(
    name="PM Agent",
    description="Decides intent/domain and routes to TL agents",
    url="http://localhost:9001/",
    version="1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
)

handler = DefaultRequestHandler(
    agent_executor=PMExecutor(),
    task_store=InMemoryTaskStore(),
)

app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler)

if __name__ == "__main__":
    uvicorn.run(app.build(), port=9001)
