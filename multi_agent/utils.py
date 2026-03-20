# utils.py — Shared utility for all agents

import httpx


async def call_agent(url: str, msg: str) -> tuple[str | None, dict | None]:
    """
    Send a JSON-RPC message/send request to an A2A agent.
    Returns (text, None) on success, or (None, error_dict) on failure.
    """
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
            timeout=30.0,
        )

    data = response.json()

    if "result" not in data:
        return None, data

    text = data["result"]["parts"][0]["text"]
    return text, None


def extract_msg(context) -> str:
    """Safely extract text from A2A message context."""
    part = context.message.parts[0]
    part_dict = part.model_dump()
    return part_dict.get("text") or part_dict.get("root", {}).get("text", "")
