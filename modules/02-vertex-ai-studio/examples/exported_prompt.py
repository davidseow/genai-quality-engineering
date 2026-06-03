"""
Exported from Vertex AI Studio — starting point for Module 03.
Run:  python exported_prompt.py
"""

import json
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

PROJECT_ID = "YOUR_PROJECT_ID"   # replace with your project
LOCATION = "us-central1"

SYSTEM_INSTRUCTION = """
You are a customer support triage assistant.
Given a support ticket, you will:
1. Classify urgency as: low, medium, or high.
2. Identify the main topic in three words or fewer.
3. Draft a polite, concise reply of no more than 100 words.

Never include the customer's name or any personal details in the reply.
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "urgency": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Urgency level of the support ticket",
        },
        "topic": {
            "type": "string",
            "description": "Main topic in three words or fewer",
        },
        "reply": {
            "type": "string",
            "description": "Polite, concise reply of no more than 100 words",
        },
    },
    "required": ["urgency", "topic", "reply"],
}

SAMPLE_TICKET = """
Subject: Order hasn't arrived — been 3 weeks!
Body: I placed order #98234 on the 1st of May. It is now the 22nd and nothing
has arrived. I have a birthday event this weekend and I desperately need the
item. Please help urgently.
"""


def main() -> None:
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    model = GenerativeModel(
        model_name="gemini-1.5-pro",
        system_instruction=SYSTEM_INSTRUCTION,
    )

    config = GenerationConfig(
        temperature=0.2,
        top_p=0.95,
        max_output_tokens=300,
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
    )

    response = model.generate_content(SAMPLE_TICKET, generation_config=config)
    result = json.loads(response.text)
    print(f"Urgency : {result['urgency']}")
    print(f"Topic   : {result['topic']}")
    print(f"Reply   : {result['reply']}")


if __name__ == "__main__":
    main()
