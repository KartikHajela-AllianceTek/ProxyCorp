import asyncio
import operator
import os
from typing import Annotated, TypedDict, List

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools


# # Azure OpenAI

llm = AzureChatOpenAI(
    azure_deployment="gpt-4o",
    temperature=0
)


class SwarmState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]


async def main():

    server = StdioServerParameters(
        command="python",
        args=["mcp_server.py"]
    )

    async with stdio_client(server) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            mcp_tools = await load_mcp_tools(session)

            tool_node = ToolNode(mcp_tools)

            # -------------------------
            # AGENT
            # -------------------------
            agent = llm.bind_tools(
                mcp_tools,
                tool_choice="auto"
            )

            def agent_node(state: SwarmState):

                response = agent.invoke(
                    [SystemMessage(content="""
You are an enterprise coordination AI.

Steps:
1) Find employee using expertise
2) Check schedule
3) Send email or schedule meeting

Always use tools.
""")] + state["messages"]
                )

                return {"messages": [response]}

            def router(state: SwarmState):

                last = state["messages"][-1]

                if hasattr(last, "tool_calls") and last.tool_calls:
                    return "tools"

                return END

            graph = StateGraph(SwarmState)

            graph.add_node("agent", agent_node)
            graph.add_node("tools", tool_node)

            graph.set_entry_point("agent")

            graph.add_conditional_edges("agent", router)
            graph.add_edge("tools", "agent")

            app = graph.compile()

            print("🐝 Swarm Ready\n")

            while True:

                q = input("\nRequest: ")

                if q == "q":
                    break

                async for output in app.astream(
                    {"messages": [HumanMessage(content=q)]},
                    {"recursion_limit": 30}
                ):

                    for node, values in output.items():

                        msg = values["messages"][-1]

                        if hasattr(msg, "tool_calls") and msg.tool_calls:

                            print("🔧 TOOL:", msg.tool_calls[0]["name"])

                        elif msg.content:
                            print("🤖", msg.content)


if __name__ == "__main__":
    asyncio.run(main())