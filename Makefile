.DEFAULT_GOAL := help

# ── paths ──────────────────────────────────────────────────────────────────────
TRIAGE_DIR   := modules/03-python-scripting/examples
EVAL_TESTS   := modules/05-evaluation-testing/examples/tests

# ── help ───────────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo "Usage: make <recipe>"
	@echo ""
	@echo "  install   Install app + dev dependencies (requires uv)"
	@echo "  start     Run the triage app  (requires GCP_PROJECT_ID)"
	@echo "  eval      Run structural evaluation tests (no API calls)"

# ── install ────────────────────────────────────────────────────────────────────
.PHONY: install
install:
	uv sync --all-groups

# ── start ──────────────────────────────────────────────────────────────────────
.PHONY: start
start:
	PYTHONPATH=$(TRIAGE_DIR) uv run python -m triage

# ── eval ───────────────────────────────────────────────────────────────────────
.PHONY: eval
eval:
	PYTHONPATH=$(TRIAGE_DIR) uv run pytest $(EVAL_TESTS) -v
