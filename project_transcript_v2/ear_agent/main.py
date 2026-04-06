import uvicorn
from a2a.types import AgentCard, AgentCapabilities, Part, TextPart
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.server.apps import A2AStarletteApplication

# Import the executor we built
from agent_executor import EarExecutor

def main(host='127.0.0.1', port=10001):
    
    # 1. Define the Agent Card
    agent_card = AgentCard(
        name="ProxyCorp Ear Agent",
        description="Handles raw audio transcription, VAD gating, and dynamic model switching.",
        url=f"http://{host}:{port}/",
        defaultInputModes=["text/plain", "application/json"], # Added
        defaultOutputModes=["text/plain", "application/json"], # Added
        skills=[], # Added
        version="1.0.0",
        capabilities=AgentCapabilities()
    )

    # 2. Mount the Executor to the Request Handler
    request_handler = DefaultRequestHandler(
        agent_executor=EarExecutor(),
        task_store=InMemoryTaskStore()
    )

    # 3. Build the Server
    server = A2AStarletteApplication(
        http_handler=request_handler,
        agent_card=agent_card
    )

    print(f"🎧 [EAR AGENT] Starting up on port {port}...")
    uvicorn.run(server.build(), host=host, port=port)

if __name__ == "__main__":
    main()