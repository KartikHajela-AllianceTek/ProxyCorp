# hr_junior/main.py

import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from a2a.server.agent_execution import AgentExecutor
from a2a.utils import new_agent_text_message


class HRJuniorExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        msg = context.message.parts[0].model_dump().get("text", "").lower()

        result = "HR Junior: Candidate screening started"

        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(self, context, event_queue):
        raise Exception("cancel not supported")


skill = AgentSkill(
    id="hr_junior",
    name="HR Junior",
    description="Handles candidate screening",
    tags=["HR JUNIOR"],
)

agent_card = AgentCard(
    name="HR Junior Agent",
    description="Handles initial hiring steps",
    url="http://localhost:9005/",
    version="1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
)

handler = DefaultRequestHandler(
    agent_executor=HRJuniorExecutor(),
    task_store=InMemoryTaskStore(),
)

app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=handler,
)

if __name__ == "__main__":
    uvicorn.run(app.build(), port=9005)
