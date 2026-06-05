# Module 01b — Test Data Management for AI

**Duration:** ~45 minutes

---

## Learning Outcome

By the end of this module you will be able to build a versioned, labelled
golden set for a GenAI component, store it in a format that travels with
your code, handle PII safely, and know when your test data is no longer
representative of production traffic.

---

## Why AI Test Data Is Different

For traditional software, test data is usually small and generated inline:
```python
assert add(2, 3) == 5
```

For GenAI, **test data is the specification**. The model has no hard-coded
logic — its "behaviour" only becomes observable through examples. This means:

| Traditional testing | GenAI testing |
|--------------------|---------------|
| Test data is generated in code | Test data is collected and labelled |
| A failing test has a clear root cause | A failing test may mean model drift, prompt change, or data shift |
| Test data is cheap to create | Good labelled test data is expensive and requires domain expertise |
| Tests are stable | Tests can become stale as the world changes |

---

## The Golden Set: Your Core Test Asset

A **golden set** is a curated dataset of (input, expected output) pairs that
captures the breadth of inputs your system will see in production. It is the
AI equivalent of a regression suite.

### How Large Should It Be?

| Urgency | Minimum recommended |
|---------|-------------------|
| Per classification class | 20 examples |
| Edge cases (boundary, adversarial) | 10 examples |
| Non-English inputs (if in scope) | 10 examples |
| Total for the triage assistant | ~80 examples to start |

Three examples (as the course started with) gives false confidence. With three
examples, a broken classifier that always returns "high" will pass 33% of tests.
With 20 per class, a broken classifier passes 33% of tests — but the failure
message clearly shows the systematic error.

### Who Labels It?

The golden set should be labelled by **subject-matter experts**, not by running
the model. Using the model to generate its own expected outputs creates circular
validation — you are testing whether the model agrees with itself, not whether
it is correct.

A practical approach:

1. **Collect real examples** — sample 100 tickets from production (or generate
   realistic synthetic ones if you are pre-launch).
2. **Label independently** — two people label each ticket for urgency, without
   discussing their answers first.
3. **Measure inter-rater agreement** — count how many tickets both labellers
   agreed on, then divide by the total. Aim for ≥ 80% agreement. If two
   people agree on 8 out of 10 tickets, that is 80%. Anything below 80%
   usually means the urgency definition is too vague — clarify it with
   examples before labelling more.

   Cohen's kappa is a more rigorous version of this measure that accounts
   for the chance of accidentally agreeing. Use it when you need to document
   label quality formally (e.g., in a model card for an audit).
4. **Resolve disagreements** — for tickets where labellers disagreed, discuss
   and either: agree on a label, or exclude the example from the golden set.
5. **Document edge cases** — flag examples where the "correct" label is
   genuinely debatable. These are your most valuable test cases.

---

## Step 1 — Store Test Data as JSONL in Version Control

**What is JSONL?** JSONL (JSON Lines) is a plain text file where each line is
a complete, valid JSON object. It is easy to append to without rewriting the
whole file, easy to version-control line-by-line, and easy to stream one
record at a time without loading the entire file into memory. Example:
```
{"subject": "order late", "expected_urgency": "high"}
{"subject": "returns query", "expected_urgency": "low"}
```
Each line can be parsed independently with `json.loads(line)`.

Never hardcode test data in Python files. Store it as JSONL alongside the
prompt files so that prompt changes and data changes travel together in the
same commit.

```
modules/05-evaluation-testing/examples/tests/
└── golden_set/
    ├── v1.jsonl          ← current golden set
    └── archive/
        └── v0.jsonl      ← previous version (kept for audit)
```

This directory already exists in the repository. You will use it in Module 05.
For now, open `v1.jsonl` to see the format — each line is one labelled example.

Each line in `v1.jsonl`:
```json
{"subject": "Order hasn't arrived in 3 weeks", "body": "I have an event this weekend, please help urgently.", "expected_urgency": "high", "notes": "Time-sensitive + emotional signal"}
{"subject": "General question about returns policy", "body": "How many days do I have to return an item?", "expected_urgency": "low", "notes": "No urgency signals"}
{"subject": "Wrong colour received", "body": "I ordered blue but got red. Would like to exchange.", "expected_urgency": "medium", "notes": "Problem but not time-sensitive"}
```

The `notes` field is for your team — it explains *why* this example has that
label, which is invaluable when a test fails months later and nobody remembers
the original reasoning.

---

## Step 2 — Load the Golden Set in Your Tests

```python
# tests/golden_set/loader.py
import json
import pathlib
from dataclasses import dataclass
from typing import Iterator


@dataclass
class GoldenExample:
    subject: str
    body: str
    expected_urgency: str
    notes: str = ""


def load(version: str = "v1") -> list[GoldenExample]:
    path = pathlib.Path(__file__).parent / f"{version}.jsonl"
    return [
        GoldenExample(**json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
```

Using this in tests:
```python
import pytest
from tests.golden_set.loader import load

@pytest.mark.parametrize("example", load("v1"), ids=lambda e: e.subject[:40])
def test_urgency_classification(example):
    result = triage_ticket(SupportTicket(example.subject, example.body), project_id=PROJECT_ID)
    assert result.urgency.value == example.expected_urgency, (
        f"Expected {example.expected_urgency!r} — Notes: {example.notes}"
    )
```

The `ids=` argument makes each test case identifiable by ticket subject in
CI output, so failures are easy to locate without digging into indices.

---

## Step 3 — Versioning the Golden Set

**Rule: when the prompt changes, the golden set version may need to change.**

A prompt change that intentionally alters behaviour (e.g., reclassifying
ambiguous tickets as "medium" instead of "low") should be accompanied by a
golden-set update in the same pull request. This makes the change explicit and
reviewable.

Version-bumping checklist:
- [ ] Did the expected outputs change for any existing examples? → update or add notes
- [ ] Did you add new behaviour (e.g., a new language)? → add examples for it
- [ ] Is the old golden set still valid? → keep it in `archive/` for audit

When NOT to version-bump: adding more examples of the same type that already
exists. That is a golden-set expansion, not a version change.

---

## Step 4 — Handling PII in Test Data

Support tickets often contain names, addresses, order numbers, and other PII.
Storing real customer data in a test dataset in source control is a GDPR and
data governance violation.

Options, in order of preference:

| Approach | How | When to use |
|----------|-----|------------|
| **Synthetic data** | Generate realistic but fictitious tickets | Pre-launch or when you control the domain |
| **Anonymisation** | Replace names/addresses with `[NAME]`, `[ADDRESS]` | When using real samples post-launch |
| **Data masking** | Swap real values for fake-but-realistic ones | When preserving linguistic naturalness matters |

A simple anonymiser:
```python
import re

def anonymise(text: str) -> str:
    text = re.sub(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[NAME]', text)         # "Sarah Johnson"
    text = re.sub(r'\b\d{1,5} [A-Z][a-z]+ (Street|Road|Lane|Avenue)\b', '[ADDRESS]', text)
    text = re.sub(r'\b[Oo]rder\s*#?\d{4,}\b', 'Order #[ID]', text)
    return text
```

Always run anonymisation **before** storing to the golden set, not at test
runtime. Storing un-anonymised data, even temporarily, creates risk.

---

## Step 5 — Detecting When Your Test Data Is Stale

A golden set becomes stale when production traffic drifts away from it. Signals
to watch for:

- **New ticket categories** appear in production that have no golden-set
  examples (monitor classification distribution in Module 06).
- **Seasonal changes** — a retailer's support tickets look different in
  December than in July.
- **Product changes** — a new product line introduces new failure modes not
  covered by existing tests.

A quarterly review process:
1. Sample 50 recent production tickets (anonymised).
2. Label them using the same process as Step 1.
3. Compare the distribution to the golden set. If real distribution differs by
   more than 20% in any class, expand the golden set.
4. Look for new ticket types that have no golden-set examples — add them.

---

## Exercise

1. Open `modules/05-evaluation-testing/examples/tests/golden_set/v1.jsonl`.
2. Review the existing examples. Are they balanced across urgency levels?
3. Add five more examples based on tickets from your risk register (Module 01).
   Write a `notes` field for each explaining the labelling decision.
4. Write a `loader.py` that reads the JSONL and returns a list of
   `GoldenExample` dataclass instances.
5. Identify one field in the example tickets that could contain PII. Apply
   the anonymiser function to sanitise it before storing.
