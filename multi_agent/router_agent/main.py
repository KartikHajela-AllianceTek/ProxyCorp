# router_agent/main.py
import uvicorn
import httpx

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from a2a.server.agent_execution import AgentExecutor
from a2a.utils import new_agent_text_message
from groq import Groq
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

from groq import Groq

API_KEY = os.getenv("API_KEY")

client = Groq(api_key=API_KEY)


def decide_route(msg):
    prompt = f"""
    You are a router.

    Decide which department should handle this request:
    - PM → meetings, projects
    - HR → hiring, recruitment
    - BA → requirements

    Respond ONLY with one word: PM or HR or BA

    Input: {msg}
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content.strip()


class RouterExecuter(AgentExecutor):
    async def execute(self, context, event_queue):
        # msg = context.message.parts[0].model_dump().get("Text", "").lower()
        part = context.message.parts[0]
        part_dict = part.model_dump()
        msg = part_dict.get("text") or part_dict.get("root", {}).get("text", "")
        msg = msg.lower()

        decision = await asyncio.to_thread(decide_route, msg)

        if "PM" in decision:
            url = "http://localhost:9001/"
            label = "PM"

        elif "HR" in decision:
            url = "http://localhost:9004/"
            label = "HR"

        else:
            result = "Router: Could not determine department"
            await event_queue.enqueue_event(new_agent_text_message(result))
            return

        # 🔥 CALL SELECTED AGENT
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
            result = f"Router → Error from {label}: {data}"
        else:
            text = data["result"]["parts"][0]["text"]
            result = f"Router → {text}"

        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(self, context, event_queue):
        raise Exception("cannot cancel")


skill = AgentSkill(
    id="router",
    name="Router",
    description="Routers Queries",
    tags=["Router Agent"],
)

agent_card = AgentCard(
    name="Router Agent",
    description="Routes to PM",
    url="http://localhost:9000",
    version="1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
)

handler = DefaultRequestHandler(
    agent_executor=RouterExecuter(),
    task_store=InMemoryTaskStore(),
)

app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=handler,
)

if __name__ == "__main__":
    uvicorn.run(app.build(), port=9000)
