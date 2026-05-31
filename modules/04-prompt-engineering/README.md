# Module 04 — Prompt Engineering Best Practices

**Duration:** ~45 minutes

---

## Learning Outcome

By the end of this module you will be able to apply six core prompt
engineering techniques to improve the accuracy, consistency, and safety of
your GenAI outputs.

---

## The Six Techniques

### 1. Be Explicit About Output Format

Vague instructions produce vague outputs. If you need JSON, say so — and give
an example.

**Before:**
```
Summarise this ticket and suggest a reply.
```

**After:**
```
Respond only with valid JSON matching this schema:
{"urgency": "low|medium|high", "topic": "<three words>", "reply": "<string>"}
Do not include any text outside the JSON object.
```

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

One or two examples of the desired input/output format dramatically improve
consistency.

```
Example input:
  Subject: Wrong item received
  Body: I ordered a blue mug but received a red one.

Example output:
  {"urgency": "medium", "topic": "wrong item", "reply": "We are sorry to hear
  the wrong item was sent. We will arrange a replacement and return label
  within 24 hours."}

Now process the following ticket:
```

---

### 4. Chain of Thought for Complex Decisions

For multi-step reasoning (e.g., deciding urgency), ask the model to think
step-by-step before giving the final answer.

```
First, identify any time-sensitive phrases in the ticket.
Then, identify any emotional signals (frustration, urgency).
Finally, based on those observations, classify the urgency.
Return only the final JSON — do not include your reasoning in the output.
```

---

### 5. Set a Low Temperature for Structured Outputs

For classification and JSON outputs, use `temperature=0.1` to `0.3`. Higher
values introduce unnecessary variation in fields that should be deterministic.

```python
config = GenerationConfig(temperature=0.2, max_output_tokens=300)
```

---

### 6. Defensive Output Validation

Never trust the model to always return valid JSON. Always parse with a
try/except and validate required fields.

```python
import json
from jsonschema import validate, ValidationError

SCHEMA = {
    "type": "object",
    "required": ["urgency", "topic", "reply"],
    "properties": {
        "urgency": {"enum": ["low", "medium", "high"]},
        "topic": {"type": "string"},
        "reply": {"type": "string"},
    },
}


def safe_parse(text: str) -> dict:
    try:
        data = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
        validate(instance=data, schema=SCHEMA)
        return data
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"Model returned invalid output: {exc}") from exc
```

---

## Putting It Together

See `examples/improved_prompt.py` for a version of the triage client that
applies all six techniques.

---

## Exercise

1. Open `modules/03-python-scripting/examples/triage/prompts.py`.
2. Add a two-shot few-shot example to the system instruction.
3. Update `client.py` to use `safe_parse` from this module.
4. Run the triage module again and confirm the output is still valid.
5. Deliberately send a ticket that has no subject line — observe what happens
   and decide whether your prompt handles it gracefully.
