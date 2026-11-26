import os
import requests
from dotenv import load_dotenv
from .script import COLD_CALL_SYSTEM_PROMPT

load_dotenv()

class ColdCallAgent:
    def __init__(self):
        self.api_key = os.getenv("VAPI_API_KEY")
        self.base_url = "https://api.vapi.ai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_assistant(self, name="Ironclad Cold Caller"):
        """Creates the voice assistant with your 80/20 script."""
        payload = {
            "name": name,
            "model": {
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "systemPrompt": COLD_CALL_SYSTEM_PROMPT,
                "temperature": 0.3,
            },
            "voice": {
                "provider": "11labs",
                "voiceId": "21m00Tcm4TlvDq8ikWAM",  # Professional female voice
                "stability": 0.5,
                "similarityBoost": 0.75,
            },
            "firstMessage": "Hi, is this the owner of the company? This is Sarah calling from Ironclad Logistic. Quick question — are you currently under a load, or looking for one right now?",
            "endCallPhrases": ["goodbye", "bye", "talk to you later", "have a good day"],
            "recordingEnabled": True,
        }
        response = requests.post(f"{self.base_url}/assistant", headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def make_call(self, assistant_id, phone_number, customer_name="Carrier"):
        """Makes a real phone call to a carrier."""
        payload = {
            "assistantId": assistant_id,
            "customer": {
                "number": phone_number,  # Must be in E.164 format: +1XXXXXXXXXX
            },
            "name": f"Call to {customer_name}",
        }
        response = requests.post(f"{self.base_url}/call/phone", headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def list_calls(self):
        """Get all call history."""
        response = requests.get(f"{self.base_url}/call", headers=self.headers)
        response.raise_for_status()
        return response.json()