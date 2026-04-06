from google.adk import Agent
import os

class LinguistAgent:
    def create_agent(self):
        return Agent(
            model="groq/llama-3.3-70b-versatile", 
            name="ProxyCorp_Linguist",
            instruction="""
            You monitor meeting transcripts for language shifts.
            The primary engine is English.
            If you detect a shift to Hindi or Gujarati (including Hinglish), respond ONLY with the exact command: 
            `switch_to_hindi` OR `switch_to_gujarati`.
            If the language returns to English, respond with: `switch_to_english`.
            Do not provide conversational responses. Output commands only.
            """
        )