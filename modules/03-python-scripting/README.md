# Module 03 — Reading & Understanding the Codebase

**Duration:** ~60 minutes

---

## Learning Outcome

By the end of this module you will be able to read the triage codebase,
identify every testable unit, understand what each function promises and what
it does not, and map those contracts to the test types you will write in
Module 05.

> **QE note:** You do not need to build this code from scratch. You need to
> understand it well enough to test it confidently and to catch regressions
> when it changes. That is a different — and equally important — skill.

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
└── prompts.py       ← prompt text + response schema
```

---

## Testability Analysis — What a QE Sees in This Code

After reading the codebase, a QE should produce an analysis like this. It
directly maps to the test types in Module 05.

### Pure functions — test in isolation, no API call needed

| Function | In | Out | What to test |
|----------|-----|-----|-------------|
| `_parse(text)` | JSON string | `TriageResult` | Valid JSON → correct object; bad urgency → `ValueError`; missing key → `KeyError`; unicode in reply → preserved |
| `build_user_message(ticket)` | `SupportTicket` | `str` | Subject and body appear in output; PII is preserved as-is (stripping happens elsewhere) |
| `Urgency(value)` | `str` | `Urgency` | "low"/"medium"/"high" → enum; anything else → `ValueError` — these are your boundary values |

### Functions requiring mocking — test behaviour without real API calls

| Function | What to mock | What to test |
|----------|-------------|-------------|
| `triage_ticket()` | `model.generate_content` | Happy path returns `TriageResult`; API raises → retried 3 times with correct delays; all retries fail → `RuntimeError` |

### The retry contract (test this explicitly)

`_BACKOFF = [1, 2, 4]` — the code promises:
- At most 3 attempts
- 1 second wait after attempt 1, 2 seconds after attempt 2
- After all 3 fail, raises `RuntimeError` wrapping the last exception

```python
# Test the retry contract without waiting real seconds
from unittest.mock import patch, MagicMock
import pytest
from triage.client import triage_ticket
from triage.models import SupportTicket

def test_retries_three_times_then_raises():
    ticket = SupportTicket("Test", "Test body")
    with patch("triage.client.GenerativeModel") as MockModel, \
         patch("triage.client.time.sleep") as mock_sleep:
        MockModel.return_value.generate_content.side_effect = Exception("API error")
        with pytest.raises(RuntimeError, match="All 3 attempts failed"):
            triage_ticket(ticket, project_id="test-project")
        assert MockModel.return_value.generate_content.call_count == 3
        assert mock_sleep.call_count == 2   # sleeps between attempts, not after last
```

---

## Exercise

1. Run `python -m triage` with a real GCP project and confirm it works.
2. Temporarily remove `response_mime_type` and `response_schema` from the
   config and re-run — observe the raw output. Then restore them.
3. Write the retry contract test above and run it with `make eval`. It should
   pass with no API calls.
4. Identify one more pure function in the codebase and write two tests for it.
