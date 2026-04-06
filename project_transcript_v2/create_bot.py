import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

RECALL_API_TOKEN = os.getenv("RECALL_API_TOKEN")
MEETING_URL = os.getenv("MEETING_URL")
NGROK_DOMAIN = os.getenv("NGROK_DOMAIN") # e.g., "abc1234.ngrok.app"

if not all([RECALL_API_TOKEN, MEETING_URL, NGROK_DOMAIN]):
    print("Error: Missing required environment variables (.env).")
    exit(1)

url = "https://ap-northeast-1.recall.ai/api/v1/bot/"

headers = {
    "Authorization": f"Token {RECALL_API_TOKEN}",
    "accept": "application/json",
    "content-type": "application/json"
}

# No output media logic anymore since it's just a passive listener
payload = {
    "meeting_url": MEETING_URL,
    "bot_name": "AI Meeting Scribe",
    "variant": {"microsoft_teams": "web_4_core"},
    "recording_config": {
        "audio_mixed_raw": {},
        "realtime_endpoints": [
            {
                "type": "websocket",
                "url": f"wss://{NGROK_DOMAIN}/audio",
                "events": ["audio_mixed_raw.data"]
            }
        ]
    },
    # Tell Recall to render the HTML page for the bot's camera!
    "output_media": {
        "camera": {
            "kind": "webpage",
            "config": {
                "url": f"https://{NGROK_DOMAIN}/avatar"
            }
        }
    }
}

print(f"Deploying bot to: {MEETING_URL}...")
response = requests.post(url, headers=headers, json=payload)

if response.status_code in (200, 201):
    print("✅ Successfully created Recall.ai bot!")
    print(json.dumps(response.json(), indent=2))
else:
    print(f"❌ Failed to create bot. Status code: {response.status_code}")
    print(response.text)