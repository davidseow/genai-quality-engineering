# Module 04 — Prompt Engineering Best Practices

**Duration:** ~45 minutes

---

## Learning Outcome

By the end of this module you will be able to apply six core prompt
engineering techniques to improve the accuracy, consistency, and safety of
your GenAI outputs.

---

## The Six Techniques

### 1. Enforce Output Format via the API, Not the Prompt

Telling the model to "respond in JSON" in the system instruction is unreliable
— at high temperatures or on unusual inputs the model can produce markdown
fences, extra commentary, or malformed JSON.

Use the model's **structured output** feature instead. Pass a JSON schema to
`GenerationConfig` and the model's decoding is constrained to match it:

```python
from vertexai.generative_models import GenerationConfig

config = GenerationConfig(
    temperature=0.2,
    max_output_tokens=300,
    response_mime_type="application/json",
    response_schema={
        "type": "object",
        "properties": {
            "urgency": {"type": "string", "enum": ["low", "medium", "high"]},
            "topic":   {"type": "string"},
            "reply":   {"type": "string"},
        },
        "required": ["urgency", "topic", "reply"],
    },
)
```

Benefits over a prompt instruction:
- The `urgency` field **cannot** contain a value outside the enum, even at
  temperature 1.0.
- `response.text` is always clean JSON — no markdown fences to strip.
- The schema is version-controlled alongside the code, not buried in a string.

---

### 2. Use a System Instruction for Persona and Constraints

Put stable rules in the system instruction, not the user message. The model
treats system instructions as a higher-level contract.

```python
system_instruction = """
You are a polite, concise customer support assistant.
Rules you must never break:
- Never include personal data in your reply.
- Never promise a specific delivery date you cannot confirm.
- If you are uncertain, say so and escalate.
"""
```

---

### 3. Few-Shot Examples

**"N-shot" notation:** Zero-shot means no examples (just the instruction).
One-shot means one example. Two-shot means two examples. More examples help
the model understand expected style and edge cases, but each example adds
tokens and therefore cost. Two examples is usually the right starting point
for structured classification tasks.

One or two examples of the desired input/output format dramatically improve
consistency.

```
Example input:
  Subject: Wrong item received
  Body: I ordered a blue mug but received a red one.

Example output:
  urgency: medium
  topic: wrong item received
  reply: We are sorry to hear the wrong item was sent. We will arrange a
  replacement and return label within 24 hours.

Now process the following ticket:
```

The example output does not need to be JSON — structured output handles the
format. Keep examples focused on the *content* and *reasoning* you want, not
the serialisation format.

---

### 4. Chain of Thought for Complex Decisions

For multi-step reasoning (e.g., deciding urgency), ask the model to think
step-by-step before giving the final answer.

```
First, identify any time-sensitive phrases in the ticket.
Then, identify any emotional signals (frustration, urgency).
Finally, based on those observations, classify the urgency.
Return only the final classification — do not include your reasoning in the output.
```

---

### 5. Set a Low Temperature for Structured Outputs

For classification and JSON outputs, use `temperature=0.1` to `0.3`. Higher
values introduce unnecessary variation in fields that should be deterministic.

```python
config = GenerationConfig(temperature=0.2, max_output_tokens=300)
```

---

### 6. Validate Business Rules, Not Format

With structured output enabled, `response.text` is guaranteed valid JSON that
matches the schema — you do not need to strip markdown fences or re-validate
the structure. Focus your validation on **business rules** the schema cannot
express:

```python
import json
from .models import TriageResult, Urgency


def parse_and_validate(text: str) -> TriageResult:
    data = json.loads(text)
    result = TriageResult(
        urgency=Urgency(data["urgency"]),   # raises ValueError if out of enum
        topic=data["topic"],
        reply=data["reply"],
    )
    if len(result.reply.split()) > 150:
        raise ValueError("Reply exceeds word limit — check system instruction")
    return result
```

Things worth validating at this layer:
- Word count / length limits
- Presence of forbidden content (e.g., URLs, PII patterns)
- Business-specific constraints (e.g., urgency escalation rules)

---

## Putting It Together

See `examples/improved_client.py` for a version of the triage client that
applies all six techniques. It extends `triage/client.py` with few-shot
examples, chain-of-thought reasoning in the prompt, and word-count validation
via `parse_and_validate`.

---

## Exercise

1. Open `modules/03-python-scripting/examples/triage/prompts.py`.
2. Add a two-shot example (two input/output pairs) to the system instruction.
   Remember: "two-shot" means providing two complete examples before the live
   ticket. The format does not need to be JSON — structured output handles that.
3. Open `examples/improved_client.py` and read how `parse_and_validate` adds
   word-count checking on top of the structured output guarantee.
4. Run the triage module again and confirm the output is still valid.
5. Deliberately send a ticket that has no subject line — observe what happens
   and decide whether your prompt handles it gracefully.
