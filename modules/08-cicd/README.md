# Module 08 — CI/CD for GenAI Pipelines

**Duration:** ~45 minutes

---

## Learning Outcome

By the end of this module you will have a GitHub Actions workflow that runs
structural tests on every pull request, golden-set evaluation on merge to
main, and automated deployment to Cloud Run on release.

---

## Why CI/CD Matters for GenAI

A prompt change is a code change. It can silently break downstream behaviour
in ways that only appear at runtime. CI/CD enforces:

- Structural tests run on every PR (fast, free of API calls)
- Golden-set evaluation runs on merge (catches prompt regressions)
- Deployment only happens when all gates pass

---

## Pipeline Overview

```
PR opened
  └── [ci-check] structural tests + linting

Merged to main
  └── [eval] golden-set evaluation (requires GCP)
        └── [deploy] build image → push → Cloud Run deploy
```

---

## Workflow File

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  structural-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: make install
      - run: make eval

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv run ruff check .

  golden-set-eval:
    needs: [structural-tests, lint]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
      - run: make install
      - run: PYTHONPATH=modules/03-python-scripting/examples uv run pytest modules/05-evaluation-testing/examples/tests/test_golden_set.py -v
        env:
          GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}

  deploy:
    needs: [golden-set-eval]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
      - uses: google-github-actions/setup-gcloud@v2
      - run: gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/triage-api
      - run: |
          gcloud run deploy triage-api \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/triage-api \
            --platform managed \
            --region us-central1 \
            --no-allow-unauthenticated
```

---

## Authentication Best Practice

Use **Workload Identity Federation** rather than a service account key file.
This avoids long-lived credentials in GitHub secrets.

```bash
# One-time setup
gcloud iam workload-identity-pools create "github-pool" \
  --location="global"

gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository"
```

---

## Quality Gates — Do Not Deploy Below a Threshold

Passing tests is necessary but not sufficient for deployment. Add an accuracy
gate that blocks the deploy job if the golden set falls below a threshold:

```yaml
  accuracy-gate:
    needs: [golden-set-eval]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
      - run: make install
      - name: Enforce accuracy gate
        run: |
          PYTHONPATH=modules/03-python-scripting/examples \
          GCP_PROJECT_ID=${{ secrets.GCP_PROJECT_ID }} \
          uv run python scripts/compute_accuracy.py
```

The `compute_accuracy.py` script (see Module 05) exits with code 1 if accuracy
falls below 90%, which causes the `accuracy-gate` job to fail and blocks the
`deploy` job.

---

## Handling Flaky Tests from Model Non-Determinism

Golden-set tests can be flaky if temperature is too high or the model is
inconsistent on borderline examples. Strategies:

- **Pin temperature ≤ 0.2** for all CI test runs. Add it to the test runner
  config, not just the production config.
- **Pin the model version** in config (`gemini-1.5-pro-002` not `gemini-1.5-pro`).
  Model updates can change output distribution silently.
- **Re-run on failure** — if a golden-set test fails, re-run it once before
  blocking. True regressions fail consistently; flaky tests often pass on retry.
  `pytest-rerunfailures` is already in the dev dependencies (`pyproject.toml`):
  ```yaml
  - run: uv run pytest ... --reruns 1 --reruns-delay 2
  ```
- **Flag borderline examples** — add a `"flaky": true` field in the JSONL for
  examples that regularly cause disagreement. Skip them in CI; review them
  manually in sprint demos.

---

## Prompt Change Policy

Add this to your `CONTRIBUTING.md`:

> Any change to a file in `triage/prompts.py` requires:
> 1. An updated entry in the golden-set test dataset
> 2. A comment in the PR describing what behaviour changed and why

This ensures prompt changes are intentional and reviewed.

---

## Exercise

1. Create `.github/workflows/ci.yml` using the template above.
2. Open a pull request that changes the system instruction (e.g., change the
   word "polite" to "empathetic").
3. Confirm that structural tests run and pass on the PR.
4. Merge to main and confirm the golden-set evaluation runs.
5. Add the prompt change policy to your `CONTRIBUTING.md`.
