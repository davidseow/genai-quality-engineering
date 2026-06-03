import json
import logging
import time
from typing import Optional

import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel

from .models import SupportTicket, TriageResult, Urgency
from .prompts import RESPONSE_SCHEMA, SYSTEM_INSTRUCTION, build_user_message

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
_BACKOFF = [1, 2, 4]


def triage_ticket(
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
    message = build_user_message(ticket)

    last_error: Optional[Exception] = None
    for attempt, wait in enumerate(_BACKOFF, start=1):
        try:
            response = model.generate_content(message, generation_config=config)
            return _parse(response.text)
        except Exception as exc:
            logger.warning("Attempt %d failed: %s", attempt, exc)
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(wait)

    raise RuntimeError(f"All {MAX_RETRIES} attempts failed") from last_error


def _parse(text: str) -> TriageResult:
    data = json.loads(text)
    return TriageResult(
        urgency=Urgency(data["urgency"]),
        topic=data["topic"],
        reply=data["reply"],
    )
