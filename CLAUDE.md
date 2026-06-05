# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make install          # Install all dependencies (app + dev) via uv
make eval             # Run the no-API test suite (Layers 0–2)
make start            # Run the triage CLI (requires GCP_PROJECT_ID env var)

uv run ruff check .   # Lint

# Run a single test
PYTHONPATH=modules/03-python-scripting/examples uv run pytest modules/05-evaluation-testing/examples/tests/test_structure.py::test_parse_valid_json -v

# Run all tests including GCP-dependent ones
GCP_PROJECT_ID=<project> PYTHONPATH=modules/03-python-scripting/examples uv run pytest modules/05-evaluation-testing/examples/tests/ -v
```

`PYTHONPATH=modules/03-python-scripting/examples` is required for every `pytest` or `python -m triage` invocation — the `triage` package lives there and is not installed as a proper package.

## Architecture

This is a 10-module course (Modules 00–09) teaching QEs how to test AI applications. The running example throughout is a customer support triage assistant built with Vertex AI / Gemini.

### The triage package (`modules/03-python-scripting/examples/triage/`)

The central application used by every subsequent module:

- **`models.py`** — `Urgency(str, Enum)`, `SupportTicket`, `TriageResult` dataclasses
- **`prompts.py`** — `SYSTEM_INSTRUCTION`, `RESPONSE_SCHEMA` (JSON schema for Vertex AI structured output), `build_user_message(ticket)`
- **`client.py`** — `triage_ticket(ticket, project_id)` as main entry point; `_parse(text)` as the pure-function parser (testable without API). Uses `response_mime_type="application/json"` + `response_schema` for structured output — not prompt-level JSON instructions. Implements 3-attempt exponential backoff (`_BACKOFF = [1, 2, 4]`).

Structured output means the model's JSON format is enforced at the API level via `RESPONSE_SCHEMA`, not by text in the system prompt. This is deliberate — it makes the schema version-controllable and removes the need for markdown fence stripping in `_parse`.

### Test suite (`modules/05-evaluation-testing/examples/tests/`)

Five-layer testing pyramid — Layers 0–2 require no GCP credentials and are run by `make eval`:

| Layer | File | What it tests |
|-------|------|---------------|
| 0 | `test_adversarial.py` | Boundary inputs, unicode, prompt injection (GCP tests skip without credentials) |
| 1 | `test_structure.py` | `_parse()` with valid/invalid JSON — pure unit tests |
| 2 | `test_retry.py` | Retry contract via `unittest.mock.patch`; asserts exactly 3 attempts, delays [1, 2]s |
| 3 | `golden_set/` | JSONL-driven accuracy tests (require GCP) |
| 4 | LLM-as-judge | Described in Module 05 README; not yet implemented |

The retry tests patch `vertexai.init` with an `autouse` fixture so no real SDK calls occur.

### Golden set (`modules/05-evaluation-testing/examples/tests/golden_set/`)

- `v1.jsonl` — 30 labelled examples (10 per urgency class); use `loader.load("v1")` to read
- Adding new examples: append JSONL lines; bump to `v2.jsonl` when making a breaking label change
- Any change to `triage/prompts.py` should be accompanied by a golden set update

### Course module map

```
00  Environment setup & prerequisites
01  Risk storming — risk register with Test Strategy column
01b Test data management — golden set labelling, JSONL format, PII handling
02  Vertex AI Studio — prototyping without code
03  Reading the triage codebase (code already written — QEs read, not build)
04  Prompt engineering — improved_client.py shows few-shot + chain-of-thought
05  Evaluation & testing — 5-layer pyramid, A/B eval, LLM-as-judge
06  Observability — structured logging, consistency-as-confidence proxy (3 runs, majority vote)
07  Production app — FastAPI on Cloud Run, Pub/Sub human-review queue
08  CI/CD — GitHub Actions, accuracy quality gate, flaky test handling
09  Responsible AI — safety filters, fairness tests, model card
```

### Confidence without logprobs

Gemini does not expose token logprobs. The course uses **consistency as a proxy**: run the model 3× at low temperature and take the majority vote. This is defined in Module 06 and used in Modules 07 and 09. The `confidence_threshold` config field in Module 07's `config.py` example should use `consistency_runs: int = 3` — not a raw float threshold.

## Dependency management

`uv` is the only supported tool. Do not use `pip` directly. Dev dependencies live under `[dependency-groups] dev` in `pyproject.toml`. `pytest-rerunfailures` is included there for `--reruns 1` in CI golden-set runs.

## Linting

Ruff config in `pyproject.toml`: `line-length = 100`, `target-version = "py310"`. No separate `.ruff.toml`.
