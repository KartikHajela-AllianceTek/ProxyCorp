# mobile_dev_agent/main.py  (Mobile Dev — port 9008)

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


class MobileDevExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        extract_msg(context)
        await event_queue.enqueue_event(
            new_agent_text_message("Mobile Dev: Updating Android app")
        )

    async def cancel(self, context, event_queue):
        raise Exception("cancel not supported")


skill = AgentSkill(
    id="mobile_dev",
    name="Mobile Developer",
    description="Handles Android/iOS app development",
    tags=["Dev Agent"],
)

agent_card = AgentCard(
    name="Mobile Dev Agent",
    description="Mobile Developer — handles Android/iOS tasks",
    url="http://localhost:9008/",
    version="1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
)

handler = DefaultRequestHandler(
    agent_executor=MobileDevExecutor(),
    task_store=InMemoryTaskStore(),
)

app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler)

if __name__ == "__main__":
    uvicorn.run(app.build(), port=9008)
