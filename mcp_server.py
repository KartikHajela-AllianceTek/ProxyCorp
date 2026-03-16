import json
import os
import base64
import datetime
from email.message import EmailMessage

from mcp.server.fastmcp import FastMCP

# Google API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

mcp = FastMCP("Enterprise_Data_Server")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events"
]


# -------------------------
# DATABASE LOADER
# -------------------------
def load_db(filename):
    if not os.path.exists(filename):
        return None
    with open(filename, "r") as f:
        return json.load(f)


# -------------------------
# GOOGLE AUTH
# -------------------------
def get_google_services():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    gmail_service = build("gmail", "v1", credentials=creds)
    calendar_service = build("calendar", "v3", credentials=creds)

    return gmail_service, calendar_service


# =========================================================
# DIRECTORY TOOL
# =========================================================

@mcp.tool()
def lookup_employee_by_expertise(query: str):

    db = load_db("global_directory.json")

    if isinstance(query, list):
        query = " ".join(query)

    query = query.lower()
    keywords = query.split()

    matches = []

    for emp in db:

        expertise = [e.lower() for e in emp["expertise"]]

        for word in keywords:

            if word in " ".join(expertise):

                matches.append(emp)
                break

    if matches:
        return json.dumps(matches)

    return json.dumps({"error": "No employee found"})


# =========================================================
# TIME TOOL
# =========================================================

@mcp.tool()
def get_current_time() -> str:

    now = datetime.datetime.now()

    return json.dumps({
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M")
    })


# =========================================================
# SCHEDULE TOOL
# =========================================================

@mcp.tool()
def get_calendar_free_slots(pointer_key: str, date: str) -> str:

    db = load_db("personal_db.json")

    schedule = db.get(pointer_key, {}).get("schedule", {})

    busy = schedule.get(date, [])

    return json.dumps({
        "pointer_key": pointer_key,
        "date": date,
        "busy_slots": busy
    })


# =========================================================
# EMAIL TOOL
# =========================================================

@mcp.tool()
def format_and_send_message(pointer_key: str, subject: str, context: str):

    local_db = load_db("local_db.json")
    global_db = load_db("global_directory.json")

    contact = local_db["contact_info"].get(pointer_key)

    if not contact:
        return json.dumps({"error": "Contact not found"})

    name = next(
        (emp["name"] for emp in global_db if emp["pointer_key"] == pointer_key),
        "Colleague"
    )

    template = local_db["templates"]["standard_update"]

    message_text = template.format(
        name=name,
        context=context
        
    )

    destination = contact["email"]

    gmail_service, _ = get_google_services()

    message = EmailMessage()

    message.set_content(message_text)
    message["To"] = destination
    message["From"] = "me"
    message['Subject'] = subject

    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()

    gmail_service.users().messages().send(
        userId="me",
        body={"raw": encoded}
    ).execute()

    return json.dumps({
        "status": "Email sent",
        "recipient": destination
    })


# =========================================================
# MEETING TOOL
# =========================================================

@mcp.tool()
def schedule_meeting(pointer_key: str, date: str, start_time: str, end_time: str, context: str):

    local_db = load_db("local_db.json")

    contact = local_db["contact_info"].get(pointer_key)

    if not contact:
        return json.dumps({"error": "Contact not found"})

    _, calendar_service = get_google_services()

    event = {

        "summary": f"Meeting: {context}",

        "start": {
            "dateTime": f"{date}T{start_time}:00",
            "timeZone": "Asia/Kolkata"
        },

        "end": {
            "dateTime": f"{date}T{end_time}:00",
            "timeZone": "Asia/Kolkata"
        },

        "attendees": [
            {"email": contact["email"]}
        ],

        "conferenceData": {
            "createRequest": {
                "requestId": f"swarm_{pointer_key}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"}
            }
        }
    }

    event = calendar_service.events().insert(
        calendarId="primary",
        body=event,
        sendUpdates="all",
        conferenceDataVersion=1
    ).execute()

    return json.dumps({
        "status": "Meeting scheduled",
        "meet_link": event.get("hangoutLink")
    })


if __name__ == "__main__":
    mcp.run()