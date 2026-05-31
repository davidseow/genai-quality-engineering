# Module 02 — Rapid Prototyping in Vertex AI Studio

**Duration:** ~60 minutes

---

## Learning Outcome

By the end of this module you will have iterated on a working prompt for the
support triage assistant inside Vertex AI Studio, understood the key model
parameters, and exported your prompt ready for scripting in Module 03.

---

## What Is Vertex AI Studio?

Vertex AI Studio is Google Cloud's browser-based interface for experimenting
with large language models. It lets you:

- Test prompts interactively with zero code
- Tune model parameters (temperature, top-P, max tokens) and observe the effect
- Compare outputs side-by-side
- Export a prompt directly as Python code

It is the fastest way to validate a prompt idea before committing it to a
codebase.

---

## Step 1 — Open the Prompt Gallery

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Navigate to **Vertex AI → Language → Prompt design**
3. Select **Gemini 1.5 Pro** (or the latest available model)

---

## Step 2 — Write Your First Prompt

Paste the following into the **System instruction** box:

```
You are a customer support triage assistant.
Given a support ticket, you will:
1. Classify urgency as: low, medium, or high.
2. Identify the main topic in three words or fewer.
3. Draft a polite, concise reply of no more than 100 words.

Always respond in JSON with the keys: urgency, topic, reply.
Never include the customer's name or any personal details in the reply.
```

Paste this into the **User message** box:

```
Subject: Order hasn't arrived — been 3 weeks!
Body: I placed order #98234 on the 1st of May. It is now the 22nd and nothing
has arrived. I have a birthday event this weekend and I desperately need the
item. Please help urgently.
```

---

## Step 3 — Understand the Output

A well-formed response looks like:

```json
{
  "urgency": "high",
  "topic": "delayed delivery",
  "reply": "Thank you for reaching out. We sincerely apologise for the delay
  with order #98234. Our team is investigating this now and will provide an
  update within 2 hours. We understand how important this is and will do
  everything we can to resolve it before your event."
}
```

---

## Step 4 — Tune the Parameters

| Parameter | What it controls | Try this |
|-----------|-----------------|----------|
| **Temperature** | Randomness of output | Lower to 0.2 for consistent classification |
| **Top-P** | Vocabulary breadth | Leave at default (0.95) for now |
| **Max output tokens** | Length cap | Set to 300 to avoid verbose replies |
| **Stop sequences** | Where the model stops | Add `}` to enforce JSON termination |

Experiment: raise temperature to 1.0 and re-run the same ticket five times.
Note how the `urgency` classification changes. This illustrates why temperature
matters for structured outputs.

---

## Step 5 — Test Against Your Risk Register

Go back to your risk register from Module 01. For each risk with score ≥ 10,
craft a test input designed to trigger that failure mode.

**Example — PII leakage risk:**

```
Body: Hi, I'm Sarah Johnson at 14 Oak Street. My order is late.
```

Check whether the reply contains "Sarah Johnson" or "14 Oak Street". If it
does, tighten the system instruction.

---

## Step 6 — Export as Python

Click **\<\> Get code** → **Python**. You will see something like the snippet
in `examples/exported_prompt.py`. Save this — it is your starting point for
Module 03.

---

## Exercise

1. Run the ticket above in Vertex AI Studio and confirm you get valid JSON.
2. Try three different temperature values (0.1, 0.5, 1.0) and note the
   difference in outputs.
3. Add a new test input that targets one of your risk register items.
4. Export the prompt as Python and save it to `examples/exported_prompt.py`.
