from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import SupportTicket

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


def build_user_message(ticket: SupportTicket) -> str:
    return f"Subject: {ticket.subject}\nBody: {ticket.body}"
