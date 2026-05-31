# Module 05 — Evaluation & Testing GenAI Outputs

**Duration:** ~60 minutes

---

## Learning Outcome

By the end of this module you will be able to write a test suite for a GenAI
component that covers deterministic assertions, golden-set evaluation, and
LLM-as-judge scoring — and run it in CI.

---

## Why Testing GenAI Is Different

Traditional unit tests assert that `f(x) == expected`. GenAI outputs are
non-deterministic and often free-form text. Testing requires a layered
approach:

| Layer | What it checks | When to use |
|-------|---------------|-------------|
| **Structural** | Output format is valid (JSON, required keys) | Always |
| **Deterministic** | Low-temp outputs match a fixed expected value | Classification labels |
| **Golden-set** | Output scores above a threshold on a curated dataset | Accuracy benchmarks |
| **LLM-as-judge** | A second model evaluates quality | Open-ended text quality |

---

## Layer 1 — Structural Tests

These are fast, free, and should always be green.

```python
# tests/test_structure.py
import json
import pytest
from triage.client import _parse


def test_parse_valid_json():
    raw = '{"urgency": "high", "topic": "late delivery", "reply": "We are on it."}'
    result = _parse(raw)
    assert result.urgency.value == "high"
    assert result.topic == "late delivery"
    assert len(result.reply) > 0


def test_parse_strips_markdown_fences():
    raw = '```json\n{"urgency": "low", "topic": "feedback", "reply": "Thanks!"}\n```'
    result = _parse(raw)
    assert result.urgency.value == "low"


def test_parse_raises_on_bad_urgency():
    raw = '{"urgency": "critical", "topic": "x", "reply": "y"}'
    with pytest.raises(ValueError):
        _parse(raw)
```

---

## Layer 2 — Golden-Set Evaluation

Maintain a small curated dataset of (ticket, expected_urgency) pairs. At low
temperature, the model should classify these consistently.

```python
# tests/test_golden_set.py
import os
import pytest
from triage.client import triage_ticket
from triage.models import SupportTicket, Urgency

GOLDEN_SET = [
    (
        SupportTicket("Order 3 weeks late, event tomorrow", "Please help urgently!"),
        Urgency.HIGH,
    ),
    (
        SupportTicket("General question about returns", "How long do I have to return?"),
        Urgency.LOW,
    ),
    (
        SupportTicket("Wrong colour received", "I ordered blue, got red."),
        Urgency.MEDIUM,
    ),
]

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")


@pytest.mark.skipif(not PROJECT_ID, reason="GCP_PROJECT_ID not set")
@pytest.mark.parametrize("ticket,expected_urgency", GOLDEN_SET)
def test_urgency_classification(ticket, expected_urgency):
    result = triage_ticket(ticket, project_id=PROJECT_ID)
    assert result.urgency == expected_urgency, (
        f"Expected {expected_urgency}, got {result.urgency} for: {ticket.subject}"
    )
```

---

## Layer 3 — LLM-as-Judge

For the free-text `reply` field, use a second model call to score quality.

```python
# tests/test_reply_quality.py
import os
import json
import pytest
import vertexai
from vertexai.generative_models import GenerativeModel
from triage.client import triage_ticket
from triage.models import SupportTicket

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")

JUDGE_PROMPT = """
You are evaluating a customer support reply for quality.
Score the reply on a scale of 1-5 for each criterion:
- Polite: Is the tone respectful and empathetic?
- Concise: Is it under 100 words without unnecessary filler?
- Actionable: Does it tell the customer what happens next?
- Safe: Does it avoid making specific promises it cannot keep?

Respond only with JSON: {{"polite": N, "concise": N, "actionable": N, "safe": N}}
"""


@pytest.mark.skipif(not PROJECT_ID, reason="GCP_PROJECT_ID not set")
def test_reply_quality():
    ticket = SupportTicket(
        subject="Order hasn't arrived in 3 weeks",
        body="I really need this for an event tomorrow.",
    )
    result = triage_ticket(ticket, project_id=PROJECT_ID)

    vertexai.init(project=PROJECT_ID, location="us-central1")
    judge = GenerativeModel("gemini-1.5-pro")
    judgment_raw = judge.generate_content(
        f"{JUDGE_PROMPT}\n\nReply to evaluate:\n{result.reply}"
    )
    scores = json.loads(judgment_raw.text.strip())

    assert scores["polite"] >= 4, f"Reply not polite enough: {result.reply}"
    assert scores["safe"] >= 4, f"Reply made unsafe promises: {result.reply}"
```

---

## Running the Tests

```bash
# Structural tests only (no API calls)
pytest tests/test_structure.py -v

# All tests (requires GCP credentials)
GCP_PROJECT_ID=your-project pytest tests/ -v
```

---

## Exercise

1. Copy the test files above into `modules/05-evaluation-testing/examples/tests/`.
2. Run the structural tests and confirm they pass without any API calls.
3. Add two more entries to `GOLDEN_SET` based on your risk register.
4. Add a structural test that asserts the reply is never longer than 150 words.
