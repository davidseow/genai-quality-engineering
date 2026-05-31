# Module 00 — Course Overview & Prerequisites

**Duration:** ~15 minutes

---

## Learning Outcome

By the end of this module you will have a working local environment, a Google
Cloud project connected to Vertex AI, and a clear map of what you will build
throughout the course.

---

## What You Will Build

Across this course you will build a **customer support triage assistant** — a
GenAI-powered app that reads incoming support tickets, classifies them by
urgency and topic, drafts a suggested response, and logs everything for human
review.

You will build it progressively:

| Stage | Where |
|-------|-------|
| First prompt idea, tested interactively | Vertex AI Studio (Module 02) |
| Reproducible script | Python (Module 03) |
| Robust, tested, monitored service | Production app (Module 07) |

---

## Setting Up Your Environment

### 1. Clone the repository

```bash
git clone https://github.com/your-org/genai-quality-engineering.git
cd genai-quality-engineering
```

### 2. Install dependencies with uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you
do not have it yet:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install all dependencies (app + dev):

```bash
make install
# equivalent to: uv sync --all-groups
```

`uv` creates and manages the virtual environment automatically in `.venv`.

### 3. Authenticate with Google Cloud

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### 4. Enable the Vertex AI API

```bash
gcloud services enable aiplatform.googleapis.com
```

### 5. Verify the setup

```bash
uv run python shared/utils/verify_setup.py
```

You should see:

```
✓ Python 3.10+
✓ Google credentials found
✓ Vertex AI API reachable
Ready to go!
```

---

## Exercise

Open `shared/utils/verify_setup.py` and read through it. Note how it checks
each dependency. You will write similar health-checks for your production app
in Module 07.
