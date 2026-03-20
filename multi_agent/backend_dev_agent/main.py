# backend_dev_agent/main.py  (Backend Dev — port 9007)

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from a2a.server.agent_execution import AgentExecutor
from a2a.utils import new_agent_text_message

from utils import extract_msg


class BackendDevExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        extract_msg(context)
        await event_queue.enqueue_event(
            new_agent_text_message("Backend Dev: Building API")
        )

    async def cancel(self, context, event_queue):
        raise Exception("cancel not supported")


skill = AgentSkill(
    id="backend_dev",
    name="Backend Developer",
    description="Builds APIs and backend services",
    tags=["Dev Agent"],
)

agent_card = AgentCard(
    name="Backend Dev Agent",
    description="Backend Developer — handles API and server-side tasks",
    url="http://localhost:9007/",
    version="1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
)

handler = DefaultRequestHandler(
    agent_executor=BackendDevExecutor(),
    task_store=InMemoryTaskStore(),
)

app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler)

if __name__ == "__main__":
    uvicorn.run(app.build(), port=9007)
