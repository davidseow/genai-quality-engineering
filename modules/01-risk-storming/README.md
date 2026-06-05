# Module 01 — Risk-Storming for GenAI

**Duration:** ~45 minutes

---

## Learning Outcome

By the end of this module you will be able to run a structured risk-storming
session for a GenAI feature, produce a risk register, and use it to shape
your prompt and evaluation strategy.

---

## Why Risk-Storm Before You Prototype?

GenAI outputs are probabilistic. Unlike deterministic software, the same input
can produce different outputs across calls. Before writing a single prompt it
is worth asking: *what could go wrong, and how bad would it be?*

Risk-storming surfaces these concerns early — when they are cheap to address —
rather than after you have already shipped.

---

## The Risk-Storming Process

### Step 1 — Define the feature in one sentence

Write a plain-English description of what your GenAI feature does.

**Example:**
> "Classify incoming support tickets by urgency (low / medium / high) and
> draft a suggested reply."

### Step 2 — Brainstorm failure modes (10 minutes, no filtering)

Gather your team (or work alone) and list everything that could go wrong.
Prompt yourselves with these categories:

| Category | Questions to ask |
|----------|-----------------|
| **Accuracy** | Could the model misclassify a ticket? How often? |
| **Safety** | Could the model produce harmful or offensive output? |
| **Privacy** | Does the input contain PII that the model might echo back? |
| **Reliability** | What happens if the model API is unavailable? |
| **Cost** | Could a spike in traffic cause unexpected API costs? |
| **Bias** | Could outputs be systematically unfair to certain users? |
| **Latency** | Is the response time acceptable to users? |

### Step 3 — Score each risk

For each failure mode, assign:

- **Likelihood**: 1 (rare) → 5 (very likely)
- **Impact**: 1 (negligible) → 5 (severe)
- **Risk score** = Likelihood × Impact

### Step 4 — Decide on mitigations

For any risk with a score ≥ 10, define a mitigation before prototyping.

---

## Concrete Example — Support Triage Assistant

| # | Failure Mode | Likelihood | Impact | Score | Mitigation | Test Strategy |
|---|--------------|------------|--------|-------|------------|---------------|
| 1 | Misclassifies high-urgency ticket as low | 3 | 5 | 15 | Route low-confidence results for human review | Golden-set: ≥20 high-urgency tickets; assert ≥90% correct |
| 2 | Drafted reply contains PII from ticket body | 2 | 5 | 10 | Strip PII before sending to model | Adversarial test: inject `[NAME]` and `[ADDRESS]` into body; assert absent from reply |
| 3 | Model API rate-limit during traffic spike | 3 | 3 | 9 | Retry with exponential back-off and queue | Unit test: mock API to return 429 three times; assert RuntimeError raised after max retries |
| 4 | Offensive language in drafted reply | 2 | 4 | 8 | Enable Vertex AI safety filters | Integration test: send borderline input; assert `finish_reason != SAFETY` handling works |
| 5 | Incorrect product name in reply | 4 | 2 | 8 | Ground replies with a product knowledge base | Golden-set: tickets mentioning products; review reply manually in sprint demo |
| 6 | Model version update silently breaks classifications | 3 | 4 | 12 | Pin model version in config; never use "latest" | Regression test: re-run full golden set on every model version bump; block if accuracy drops |

---

## Risk Register Template

Copy `examples/risk_register_template.md` into your project and fill it in.

---

## How This Shapes Your Work

The mitigations you define here become:

- **Prompt constraints** (Module 04) — e.g., "never include customer names in
  the response"
- **Test cases** (Module 05) — e.g., a test that sends a high-urgency ticket
  and asserts the classification is correct
- **Monitoring alerts** (Module 06) — e.g., alert when confidence drops below
  threshold

---

## Exercise

1. Read the one-sentence description of the support triage assistant above.
2. Copy `examples/risk_register_template.md` and add at least five failure
   modes of your own.
3. Score each one and define a mitigation for any risk ≥ 10.
4. For every risk ≥ 10, fill in the **Test Strategy** column — describe in one
   sentence how you will know the mitigation is working. You will learn these
   in detail in Module 05; for now, here is enough to choose:

   - **Golden-set test** — run a labelled dataset of real examples through the
     model and check accuracy (e.g. "≥90% of high-urgency tickets classified
     correctly").
   - **Adversarial test** — send hostile or edge-case inputs and check the
     system does not break (e.g. "prompt injection in the ticket body does not
     appear in the reply").
   - **Unit test with mocking** — test a function in isolation without calling
     the real API, by replacing the API call with a fake that returns a
     pre-defined response.
   - **Load test** — send many requests simultaneously and check the system
     does not crash or slow to an unacceptable level.
   - **Manual review** — a human checks the output. Used when automated checks
     are too subjective (e.g. "does this reply sound empathetic?").
5. Keep this document — you will refer back to it in every subsequent module.
