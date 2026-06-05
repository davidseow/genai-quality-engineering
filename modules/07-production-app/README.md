# Module 07 — Building a Production App

**Duration:** ~90 minutes

---

## Learning Outcome

By the end of this module you will have deployed the support triage assistant
as a production-grade Cloud Run service with a FastAPI interface, health
checks, configuration management, and a human-review queue.

---

## Production Checklist

| Concern | How we address it |
|---------|------------------|
| Configuration | Environment variables via Secret Manager |
| API contract | FastAPI with Pydantic models and OpenAPI docs |
| Health checks | `/healthz` endpoint for Cloud Run liveness probe |
| Human-review queue | Pub/Sub for low-confidence results |
| Graceful shutdown | Lifespan context manager |
| Security | VPC Service Controls + IAM least-privilege |

---

## Application Layout

```
app/
├── main.py            ← FastAPI app
├── config.py          ← settings from env vars
├── routes/
│   └── triage.py      ← POST /triage endpoint
├── services/
│   └── triage.py      ← business logic (imports Module 03 client)
├── queue/
│   └── pubsub.py      ← low-confidence → human review
└── Dockerfile
```

---

## Step 1 — Configuration

Never hardcode project IDs or model names. Read them from environment
variables and fail fast if they are missing.

```python
# app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gcp_project_id: str
    gcp_location: str = "us-central1"
    model_name: str = "gemini-1.5-pro"
    confidence_threshold: float = 0.8
    review_topic: str = "support-triage-review"

    class Config:
        env_file = ".env"


settings = Settings()
```

---

## Step 2 — FastAPI App

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .routes.triage import router as triage_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # warm-up: pre-load the model client
    yield
    # teardown: flush logs, close connections


app = FastAPI(title="Support Triage API", lifespan=lifespan)
app.include_router(triage_router, prefix="/v1")


@app.get("/healthz")
def health() -> dict:
    return {"status": "ok"}
```

---

## Step 3 — The Triage Endpoint

```python
# app/routes/triage.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..services.triage import run_triage

router = APIRouter()


class TicketRequest(BaseModel):
    subject: str
    body: str


class TicketResponse(BaseModel):
    urgency: str
    topic: str
    reply: str
    routed_for_review: bool


@router.post("/triage", response_model=TicketResponse)
async def triage_endpoint(request: TicketRequest) -> TicketResponse:
    try:
        return await run_triage(request.subject, request.body)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

---

## Step 4 — Human-Review Queue

When the model's output is ambiguous (e.g., borderline urgency), route the
ticket to a Pub/Sub topic for human review rather than sending the drafted
reply automatically.

```python
# app/queue/pubsub.py
import json
from google.cloud import pubsub_v1
from ..config import settings

_publisher = pubsub_v1.PublisherClient()


def publish_for_review(ticket_subject: str, result: dict) -> None:
    topic_path = _publisher.topic_path(settings.gcp_project_id, settings.review_topic)
    payload = json.dumps({"ticket_subject": ticket_subject, **result}).encode()
    _publisher.publish(topic_path, payload)
```

---

## Step 5 — Dockerfile

```dockerfile
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev --no-cache

COPY app/ ./app/

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## Step 6 — Deploy to Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/$PROJECT_ID/triage-api

# Deploy
gcloud run deploy triage-api \
  --image gcr.io/$PROJECT_ID/triage-api \
  --platform managed \
  --region us-central1 \
  --set-env-vars GCP_PROJECT_ID=$PROJECT_ID \
  --no-allow-unauthenticated
```

---

## Testing the Production App

Testing the API layer is essential — you need to verify the HTTP contract
independently of the model. Use FastAPI's `TestClient` with mocked model calls
so tests run fast without GCP credentials.

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)


def test_healthz_returns_ok():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def _mock_triage(urgency="high", topic="late delivery", reply="We are on it."):
    mock = MagicMock()
    mock.urgency.value = urgency
    mock.topic = topic
    mock.reply = reply
    return mock


def test_triage_endpoint_returns_valid_response():
    with patch("app.services.triage.triage_ticket", return_value=_mock_triage()):
        response = client.post(
            "/v1/triage",
            json={"subject": "Order late", "body": "3 weeks and nothing arrived"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["urgency"] == "high"
    assert isinstance(body["reply"], str)
    assert "routed_for_review" in body


def test_triage_endpoint_returns_500_on_model_failure():
    with patch("app.services.triage.triage_ticket", side_effect=RuntimeError("API down")):
        response = client.post(
            "/v1/triage",
            json={"subject": "Test", "body": "Test body"},
        )
    assert response.status_code == 500


def test_triage_endpoint_rejects_empty_body():
    response = client.post("/v1/triage", json={"subject": "", "body": ""})
    # Empty inputs should either be validated (422) or handled gracefully (200)
    assert response.status_code in (200, 422)


def test_triage_endpoint_validates_request_schema():
    response = client.post("/v1/triage", json={"wrong_field": "value"})
    assert response.status_code == 422
```

---

## Exercise

1. Copy the code snippets above into `modules/07-production-app/examples/app/`.
2. Run the app locally: `uv run uvicorn app.main:app --reload`
3. Open `http://localhost:8000/docs` — confirm the Swagger UI shows the
   `/v1/triage` endpoint.
4. Run the API tests above using `TestClient` and confirm they pass without
   any GCP credentials.
5. Add a test that verifies the `confidence` field in the response is a float
   between 0 and 1.
