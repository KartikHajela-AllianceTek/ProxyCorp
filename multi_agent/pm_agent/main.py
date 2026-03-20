# pm_agent/main.py
from unittest import result
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import AgentCard, AgentCapabilities, AgentSkill

from logic import PMLogic
from a2a.server.agent_execution import AgentExecutor
from a2a.utils import new_agent_text_message
from icecream import ic
import httpx
from dotenv import load_dotenv
import asyncio
import os

load_dotenv()

from groq import Groq

API_KEY = os.getenv("API_KEY")

client = Groq(api_key=API_KEY)


def decide_domain(msg):
    prompt = f"""
        You are a project manager.
    
        Decide which team should handle this request:
        - AI
        - ANDROID
    
        Respond ONLY with one word: AI or ANDROID
    
        Input: {msg}
        """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content.strip()


def decide_intent(msg):
    prompt = f"""
    You are a project manager.

    Classify the request into ONE of these:
    - PROJECT → new project, planning, discussion
    - FEATURE → feature addition, bug fix, implementation

    Respond ONLY with one word: PROJECT or FEATURE

    Input: {msg}
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content.strip()


class PMExecuter(AgentExecutor):
    def __init__(self):
        self.logic = PMLogic()

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
        slots = [s.strip() for s in text.split(",")]

        return slots, None

    async def execute(self, context, event_queue):

        # ----------- Extract message safely -----------
        part = context.message.parts[0]
        part_dict = part.model_dump()

        msg = part_dict.get("text") or part_dict.get("root", {}).get("text", "")
        msg = msg.lower()

        # ----------- LLM Decisions (run in thread) -----------
        domain_answer = await asyncio.to_thread(decide_domain, msg)
        intent_answer = await asyncio.to_thread(decide_intent, msg)

        domain = domain_answer.strip().upper()
        intent = intent_answer.strip().upper()

        # ----------- Normalize domain -----------
        if "AI" in domain:
            domain = "AI"
        elif "ANDROID" in domain:
            domain = "ANDROID"
        else:
            domain = "UNKNOWN"

        # ----------- Agent mapping -----------
        agent_map = {
            "AI": ("http://localhost:9002/", "AI TL"),
            "ANDROID": ("http://localhost:9003/", "ANDROID TL"),
        }

        if domain not in agent_map:
            result = "PM: Could not determine domain"
            await event_queue.enqueue_event(new_agent_text_message(result))
            return

        url, tl_name = agent_map[domain]

        # ----------- INTENT: PROJECT vs FEATURE -----------

        # 🟢 PROJECT → only PM ↔ TL discussion
        if "PROJECT" in intent:
            # call TL (no dev delegation)
            _, error = await self.call_agent(url, msg)

            if error:
                result = f"PM: Error contacting {tl_name} {error}"
            else:
                result = f"PM: Meeting required with {tl_name}"

        # 🔵 FEATURE → go deeper (TL → dev → result)
        elif "FEATURE" in intent:
            tl_slots, error = await self.call_agent(url, msg)

            if error:
                result = f"PM: ERROR FROM {tl_name} {error}"

            else:
                pm_slots = self.logic.calendar["pm"]
                common = self.logic.find_common_slot(pm_slots, tl_slots)

                if common:
                    result = f"PM: Meeting scheduled with {tl_name} at {common}"
                else:
                    result = f"PM: No common slot with {tl_name}"

        else:
            result = "PM: Could not determine intent"

        # ----------- Send response -----------
        await event_queue.enqueue_event(new_agent_text_message(result))

        # ----------- Debug -----------
        ic("PM MSG:", msg)
        ic("DOMAIN:", domain)
        ic("INTENT:", intent)

    async def cancel(self, context, event_queue):
        raise Exception("cancel not supported")


skill = AgentSkill(
    id="pm",
    name="Project Manager",
    description="Handles scheduling",
    tags=["PM Agent"],
)

agent_card = AgentCard(
    name="PM Agent",
    description="Handles Meetings",
    url="http://localhost:9001/",
    version="1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
)

handler = DefaultRequestHandler(
    agent_executor=PMExecuter(),
    task_store=InMemoryTaskStore(),
)

app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=handler,
)


if __name__ == "__main__":
    uvicorn.run(app.build(), port=9001)
