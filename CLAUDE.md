# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

A 10-module course teaching quality engineering (QE) for GenAI applications. The code is a teaching scaffold — intentionally minimal, with value in the *structure and patterns* rather than feature completeness. All modules progressively build a **customer support triage assistant** using Google Vertex AI's Gemini models.

## Commands

```bash
# Install all dependencies (requires uv)
make install          # runs: uv sync --all-groups

# Run fast tests (layers 0–2, no API calls, no credentials needed)
make eval

# Run all tests including golden-set (requires GCP credentials)
GCP_PROJECT_ID=your-project uv run pytest modules/05-evaluation-testing/examples/tests/ -v

# Run a single test file
uv run pytest modules/05-evaluation-testing/examples/tests/test_retry.py -v

# Run a single test by name
uv run pytest modules/05-evaluation-testing/examples/tests/test_structure.py::test_valid_parse -v

# Lint
uv run ruff check .

# Run the triage assistant (requires GCP credentials)
GCP_PROJECT_ID=your-project python -m triage
```

## Architecture

### Core Application

The working source lives in `modules/03-python-scripting/examples/triage/` and is reused across all later modules. It is a four-file package:

- **`models.py`** — Typed data contracts: `SupportTicket` (subject, body), `TriageResult` (urgency, topic, reply), `Urgency` enum
- **`prompts.py`** — Prompt text (`SYSTEM_INSTRUCTION`), Gemini structured output schema (`RESPONSE_SCHEMA`), and `build_user_message()`. These are **separated from the API call** so each can be tested independently.
- **`client.py`** — `triage_ticket()` calls Gemini 1.5 Pro with retry logic (3 attempts, 1s/2s backoff). Private `_parse()` function is a pure function that parses JSON into `TriageResult` — this is the key testing seam.
- **`__main__.py`** — Minimal entry point demonstrating usage.

### Key Design Patterns

**Structured output over prompt-level JSON instructions**: The code uses `response_schema` + `response_mime_type="application/json"` in `GenerationConfig`, not instructions like "respond in JSON". This enforces format at the model decoding level; the model cannot violate schema constraints.

**Pure functions as testing seams**: `_parse(text)` in `client.py` and `build_user_message(ticket)` in `prompts.py` have no side effects and no API calls, making them the primary unit-testing targets.

**Golden sets versioned alongside prompts**: `modules/05-evaluation-testing/examples/tests/golden_set/v1.jsonl` contains labelled test examples. When prompts change, the golden set version must be bumped in the same PR.

### Test Pyramid (5 Layers)

All tests are in `modules/05-evaluation-testing/examples/tests/`:

| Layer | File | API Calls | When to Run |
|-------|------|-----------|-------------|
| 0 — Adversarial | `test_adversarial.py` | No (fast path) | Every PR |
| 1 — Structural | `test_structure.py` | No | Every PR |
| 2 — Retry contract | `test_retry.py` | No (mocked) | Every PR |
| 3 — Golden-set | `test_golden_set.py` | Yes | Merge to main |
| 4 — LLM-as-judge | (template) | Yes | Merge to main |

`make eval` runs layers 0–2 only. Layers 3–4 require `GCP_PROJECT_ID`.

### Module Progression

Each module is self-contained with a `README.md` and runnable `examples/`:

```
00-overview           → environment setup
01-risk-storming      → identify failure modes before writing code
01b-test-data-mgmt    → golden sets, labelling, PII handling
02-vertex-ai-studio   → interactive prompt prototyping
03-python-scripting   → convert prototype → typed, testable code  ← core source
04-prompt-engineering → 6 techniques (structured output, few-shot, CoT, etc.)
05-evaluation-testing → 5-layer test pyramid  ← primary test suite
06-observability      → structured logging, metrics, confidence alerts
07-production-app     → FastAPI + Cloud Run (described in README, not yet implemented)
08-cicd               → GitHub Actions workflow (template only)
09-responsible-ai     → safety filters, fairness testing, model card
```

## Key Conventions

**Dependencies**: Use `uv` (not pip/poetry). `pyproject.toml` is the source of truth; `shared/requirements.txt` exists for backward compatibility only.

**Configuration**: `GCP_PROJECT_ID` and model-related settings come from environment variables. Model version is always pinned (never use `latest`). Temperature ≤0.2 for deterministic classification.

**Retry logic**: 3 attempts with exponential backoff (1s, 2s delays before attempts 2 and 3). Mock `time.sleep` in tests to verify backoff without waiting.

**Linting**: Ruff with line length 100, target Python 3.10. Run before committing.

**Test data**: Golden set examples must include a `notes` field explaining *why* a label was assigned — this is required, not optional.
