# ml_dev_agent/main.py

import uvicorn
import httpx

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from a2a.server.agent_execution import AgentExecutor
from a2a.utils import new_agent_text_message


class MLDevExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        msg = context.message.parts[0].model_dump().get("text", "").lower()

        result = "ML Dev: Working on AI feature"

        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(self, context, event_queue):
        raise Exception("Cant cancel")


skill = AgentSkill(
    id="ml_dev",
    name="ML DEV",
    description="Handles ML tasks",
    tags=["ML DEV AGENT"],
)


agent_card = AgentCard(
    name="ML DEV Agent",
    description="ML Developer Agent",
    url="http://localhost:9006",
    version="1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
)

handler = DefaultRequestHandler(
    agent_executor=MLDevExecutor(),
    task_store=InMemoryTaskStore(),
)

app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=handler,
)

if __name__ == "__main__":
    uvicorn.run(app.build(), port=9006)
