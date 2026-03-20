# android_agent/main.py
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from a2a.server.agent_execution import AgentExecutor
from a2a.utils import new_agent_text_message
from icecream import ic


class ANDROIDExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        # msg = context.message.parts[0].model_dump.get("text", "").lower()
        part = context.message.parts[0]
        part_dict = part.model_dump()
        msg = part_dict.get("text") or part_dict.get("root", {}).get("text", "")
        msg = msg.lower()

        # simulated results
        result = "3pm, 4pm"

        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(self, context, event_queue):
        raise Exception("cancel not supported")


skill = AgentSkill(
    id="ai",
    name="ANDROID TL",
    description="Handles ANDROID tasks",
    tags=["ANDROID Agent"],
)


agent_card = AgentCard(
    name="ANDROID Agent",
    description="ANDROID team lead",
    url="http://localhost:9003",
    version="1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
)

handler = DefaultRequestHandler(
    agent_executor=ANDROIDExecutor(),
    task_store=InMemoryTaskStore(),
)

app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=handler,
)

if __name__ == "__main__":
    uvicorn.run(app.build(), port=9003)
