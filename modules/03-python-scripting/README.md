# Module 03 — Scripting Prompts in Python

**Duration:** ~60 minutes

---

## Learning Outcome

By the end of this module you will have converted your Vertex AI Studio
prototype into a clean, reusable Python module with typed inputs and outputs,
basic error handling, and a retry strategy.

---

## From Script to Module

The exported code from Module 02 works, but it is a single flat script. In
production you need:

- **Typed data models** — so callers know exactly what to pass and what to
  expect back
- **Error handling** — the API can fail; your code must handle that gracefully
- **Retry logic** — transient failures should be retried automatically
- **Separation of concerns** — prompt construction, API call, and response
  parsing should be separate functions

---

## Step 1 — Define Your Data Models

```python
# triage/models.py
from dataclasses import dataclass
from enum import Enum


class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class SupportTicket:
    subject: str
    body: str


@dataclass
class TriageResult:
    urgency: Urgency
    topic: str
    reply: str
```

---

## Step 2 — Separate Prompt Construction

Keep the prompt text and the output schema out of the API call. This makes
both easy to test and update independently.

The system instruction describes *what to do* — the schema describes *what to
return*. Keeping them separate means you can tighten the schema without
touching the instructions, and vice versa.

```python
# triage/prompts.py
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


def build_user_message(ticket: "SupportTicket") -> str:
    return f"Subject: {ticket.subject}\nBody: {ticket.body}"
```

---

## Step 3 — Add Retry Logic

The Vertex AI API is reliable but not perfect. Wrap the call with a simple
exponential back-off:

```python
# triage/client.py
import time
import json
import logging
from typing import Optional

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

from .models import SupportTicket, TriageResult, Urgency
from .prompts import RESPONSE_SCHEMA, SYSTEM_INSTRUCTION, build_user_message

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_SECONDS = [1, 2, 4]


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
    for attempt, wait in enumerate(BACKOFF_SECONDS, start=1):
        try:
            response = model.generate_content(message, generation_config=config)
            return _parse_response(response.text)
        except Exception as exc:
            logger.warning("Attempt %d failed: %s", attempt, exc)
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(wait)

    raise RuntimeError(f"All {MAX_RETRIES} attempts failed") from last_error


def _parse_response(text: str) -> TriageResult:
    data = json.loads(text)
    return TriageResult(
        urgency=Urgency(data["urgency"]),
        topic=data["topic"],
        reply=data["reply"],
    )
```

---

## Step 4 — Wire It Together

```python
# triage/__main__.py
import os
from .client import triage_ticket
from .models import SupportTicket

ticket = SupportTicket(
    subject="Order hasn't arrived — been 3 weeks!",
    body=(
        "I placed order #98234 on the 1st of May. It is now the 22nd and "
        "nothing has arrived. I have a birthday event this weekend."
    ),
)

result = triage_ticket(ticket, project_id=os.environ["GCP_PROJECT_ID"])
print(f"Urgency : {result.urgency.value}")
print(f"Topic   : {result.topic}")
print(f"Reply   : {result.reply}")
```

Run it:

```bash
GCP_PROJECT_ID=your-project python -m triage
```

---

## What You Have Now

```
triage/
├── __init__.py
├── __main__.py
├── client.py        ← API call + retry
├── models.py        ← typed data classes
└── prompts.py       ← prompt text
```

This structure is small enough to understand at a glance and large enough to
extend without rewriting everything.

---

## Exercise

1. Copy the code snippets above into the `examples/triage/` folder.
2. Run `python -m triage` with a real GCP project and confirm it works.
3. Temporarily remove `response_mime_type` and `response_schema` from the
   config and re-run — observe the raw output. Then restore them.
4. Add a second test ticket from your risk register and print both results.
