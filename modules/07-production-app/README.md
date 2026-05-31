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

WORKDIR /app
COPY shared/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
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

## Exercise

1. Copy the code snippets above into `modules/07-production-app/examples/app/`.
2. Run the app locally: `uvicorn app.main:app --reload`
3. Open `http://localhost:8000/docs` — confirm the Swagger UI shows the
   `/v1/triage` endpoint.
4. Send a POST request using `curl` or the Swagger UI and confirm you get a
   valid response.
5. Add a test in `tests/` that calls the FastAPI `TestClient` against
   `/v1/triage` without making a real API call (use `unittest.mock.patch`).
