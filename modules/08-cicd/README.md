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
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r shared/requirements.txt
      - run: pytest modules/05-evaluation-testing/examples/tests/test_structure.py -v

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check .

  golden-set-eval:
    needs: [structural-tests, lint]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
      - run: pip install -r shared/requirements.txt
      - run: pytest modules/05-evaluation-testing/examples/tests/test_golden_set.py -v
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
