# pm_agent/logic.py
class PMLogic:
    def __init__(self):
        self.calendar = {
            "pm": ["3pm", "4pm"],
            "ai": ["2pm", "3pm"],
            "android": ["5pm", "4pm"],
        }

    def detect_domain(self, msg):
        if "ai" in msg:
            return "ai"
        elif "android" in msg:
            return "android"
        return "unknown"

    def find_common_slot(self, slots1, slots2):
        for slot in slots1:
            if slot in slots2:
                return slot
        return None

    def ai_agent(self):
        return self.calendar["ai"]

    def android_agent(self):
        return self.calendar["android"]

    def run(self, msg):
        domain = self.detect_domain(msg)

        if domain == "unknown":
            return "PM: Could not determine doamin"

        pm_slots = self.calendar["pm"]

        if domain == "ai":
            tl_slots = self.ai_agent()
            tl_name = "AI TL"
        else:
            tl_slots = self.android_agent()
            tl_name = "Android TL"

        common = self.find_common_slot(pm_slots, tl_slots)

        if common:
            return f"PM: Meeting scheduled with {tl_name} at {common}"
        return f"PM: No common sloth with {tl_name}"
