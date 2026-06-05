"""
Triage client demonstrating all six prompt engineering techniques from Module 04.

Differences from the base client in modules/03-python-scripting/examples:
  - Technique 2: system instruction with explicit constraints
  - Technique 3: two-shot few-shot examples
  - Technique 4: chain-of-thought instruction
  - Technique 6: parse_and_validate adds word-count check
"""

import json
import time
import logging
import os
import sys
from typing import Optional

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../03-python-scripting/examples"))
from triage.models import SupportTicket, TriageResult, Urgency

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
_BACKOFF = [1, 2, 4]

SYSTEM_INSTRUCTION = """
You are a polite, concise customer support assistant.
Rules you must never break:
- Never include the customer's name or any personal details in your reply.
- Never promise a specific delivery date you cannot confirm.
- If you are uncertain about urgency, classify as medium, not high.

Think step-by-step:
1. Identify any time-sensitive phrases in the ticket (e.g. "tonight", "tomorrow", "event").
2. Identify emotional signals (frustration, panic, explicit urgency words).
3. Based on those observations, classify urgency.
Return only the final classification — do not include your reasoning in the output.

Examples:

Input:
  Subject: Order hasn't arrived in 3 weeks
  Body: I have an event this Saturday and desperately need the item.

Output:
  urgency: high
  topic: delayed delivery
  reply: We sincerely apologise for the delay. Our team is escalating your
  order now and will provide an update within 2 hours.

Input:
  Subject: How do I return an item?
  Body: I changed my mind about a purchase made last week.

Output:
  urgency: low
  topic: returns policy
  reply: You have 30 days to return any item in its original condition. Please
  visit our returns portal to print a prepaid label.

Now process the following ticket:
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "urgency": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "topic": {"type": "string"},
        "reply": {"type": "string"},
    },
    "required": ["urgency", "topic", "reply"],
}


def parse_and_validate(text: str) -> TriageResult:
    """Parse the structured output and apply business-rule validation."""
    data = json.loads(text)
    result = TriageResult(
        urgency=Urgency(data["urgency"]),
        topic=data["topic"],
        reply=data["reply"],
    )
    if len(result.reply.split()) > 150:
        raise ValueError(f"Reply exceeds word limit ({len(result.reply.split())} words) — tighten the system instruction")
    return result


def triage_ticket_improved(
    ticket: SupportTicket,
    project_id: str,
    location: str = "us-central1",
) -> TriageResult:
    vertexai.init(project=project_id, location=location)
    model = GenerativeModel(
        model_name="gemini-1.5-pro",
        system_instruction=SYSTEM_INSTRUCTION,
    )
    config = GenerationConfig(
        temperature=0.2,
        max_output_tokens=300,
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
    )
    message = f"Subject: {ticket.subject}\nBody: {ticket.body}"

    last_error: Optional[Exception] = None
    for attempt, wait in enumerate(_BACKOFF, start=1):
        try:
            response = model.generate_content(message, generation_config=config)
            return parse_and_validate(response.text)
        except Exception as exc:
            logger.warning("Attempt %d failed: %s", attempt, exc)
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(wait)

    raise RuntimeError(f"All {MAX_RETRIES} attempts failed") from last_error


if __name__ == "__main__":
    ticket = SupportTicket(
        subject="Order hasn't arrived — been 3 weeks!",
        body="I placed order #[ID] on the 1st of May. I have a birthday event this weekend.",
    )
    result = triage_ticket_improved(ticket, project_id=os.environ["GCP_PROJECT_ID"])
    print(f"Urgency : {result.urgency.value}")
    print(f"Topic   : {result.topic}")
    print(f"Reply   : {result.reply}")
