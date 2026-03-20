# hr_agent/main.py
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.server.agent_execution import AgentExecutor
from a2a.utils import new_agent_text_message
import httpx


class HRExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        part = context.message.parts[0]
        msg = getattr(part.root, "text", "") if hasattr(part, "root") else ""
        msg = msg.lower()

        if "hire" not in msg:
            result = "HR: I handle hiring only"

        else:
            # call HR Junior
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:9005/",
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
                result = f"HR: Error from Junior {data}"
            else:
                junior_response = data["result"]["parts"][0]["text"]
                result = f"HR → {junior_response}"

        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(self, context, event_queue):
        raise Exception("cancel not supported")


skill = AgentSkill(
    id="hr",
    name="Human Resource",
    description="Handles Hiring",
    tags=["HR Agent"],
)

agent_card = AgentCard(
    name="HR Agent",
    description="Handles recruitment",
    url="http://localhost:9004",
    version="1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
)

handler = DefaultRequestHandler(
    agent_executor=HRExecutor(),
    task_store=InMemoryTaskStore(),
)

app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=handler,
)

if __name__ == "__main__":
    uvicorn.run(app.build(), port=9004)
