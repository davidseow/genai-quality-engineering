# Module 06 — Observability & Monitoring

**Duration:** ~45 minutes

---

## Learning Outcome

By the end of this module you will have instrumented your triage client with
structured logging, latency tracking, and a confidence-based alert — and
understand how to surface these signals in Google Cloud Logging and Monitoring.

---

## What to Observe in a GenAI Service

GenAI services have failure modes that traditional services do not:

| Signal | Why it matters |
|--------|---------------|
| **Latency** | Model calls are slow; p99 latency reveals tail problems |
| **Token usage** | Directly maps to cost |
| **Output validity rate** | How often does the model return valid structured output? |
| **Classification distribution** | A sudden spike in "high" urgency may indicate a prompt regression |
| **Retry rate** | High retry rate signals API instability |
| **Consistency rate** | Proxy for confidence — how often does the model agree with itself across multiple calls? |

---

## Step 1 — Structured Logging

Replace `print()` with structured JSON logs so Cloud Logging can index fields.

```python
# triage/logging_config.py
import logging
import json
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "extra"):
            log.update(record.extra)
        return json.dumps(log)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.root.setLevel(logging.INFO)
    logging.root.handlers = [handler]
```

---

## Step 2 — Instrument the Client

```python
# triage/client.py  (updated excerpt)
import time
import logging

logger = logging.getLogger(__name__)


def triage_ticket(ticket, project_id, location="us-central1"):
    start = time.perf_counter()
    result = None
    error = None

    try:
        result = _call_model(ticket, project_id, location)
        return result
    except Exception as exc:
        error = str(exc)
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        log_payload = {
            "event": "triage_ticket",
            "latency_ms": round(duration_ms, 1),
            "urgency": result.urgency.value if result else None,
            "error": error,
        }
        if error:
            logger.error("triage_ticket failed", extra={"extra": log_payload})
        else:
            logger.info("triage_ticket succeeded", extra={"extra": log_payload})
```

---

## Step 3 — Cloud Monitoring Alert

Once your service is running on Cloud Run (Module 07), create a log-based
metric for `error` events, then set an alert:

```bash
# Create the log-based metric
gcloud logging metrics create triage_errors \
  --description="Triage ticket errors" \
  --log-filter='jsonPayload.event="triage_ticket" AND jsonPayload.error!=""'

# Create an alert policy (via Console or Terraform — see examples/)
```

---

## Step 4 — Tracking Classification Distribution

Add a custom metric to detect distribution drift:

```python
from google.cloud import monitoring_v3
import time

def record_urgency(project_id: str, urgency: str) -> None:
    client = monitoring_v3.MetricServiceClient()
    series = monitoring_v3.TimeSeries()
    series.metric.type = "custom.googleapis.com/triage/urgency_classification"
    series.metric.labels["urgency"] = urgency
    series.resource.type = "global"

    point = monitoring_v3.Point()
    point.value.int64_value = 1
    now = time.time()
    point.interval.end_time.seconds = int(now)
    series.points = [point]

    client.create_time_series(
        name=f"projects/{project_id}", time_series=[series]
    )
```

Set an alert if `high` urgency exceeds 40% of total classifications over a
5-minute window — that may indicate a prompt regression or data quality issue.

---

## Step 5 — Measuring Confidence Without Logprobs

Gemini does not expose token-level logprobs, so you cannot read a confidence
score directly from the response. Instead, use **consistency as a proxy**:
run the model three times on the same input at low temperature and measure
agreement across runs.

```python
from triage.client import triage_ticket
from triage.models import SupportTicket, Urgency


def classify_with_confidence(
    ticket: SupportTicket,
    project_id: str,
    runs: int = 3,
) -> tuple[Urgency, float]:
    """Returns the most common urgency and a confidence score (0.33–1.0)."""
    results = [triage_ticket(ticket, project_id) for _ in range(runs)]
    urgencies = [r.urgency for r in results]
    most_common = max(set(urgencies), key=urgencies.count)
    confidence = urgencies.count(most_common) / runs
    return most_common, confidence
```

Usage in the routing decision:
```python
urgency, confidence = classify_with_confidence(ticket, project_id)
if confidence < 0.67:          # 2/3 or fewer agreed
    publish_for_review(ticket, urgency, confidence)
else:
    send_reply(urgency)
```

**Trade-off:** This costs 3× the API calls and adds latency. Use it for tickets
where the cost of a wrong classification is high — e.g., `high` urgency
misclassified as `low`. Log the confidence score for every request so you can
track it over time.

---

## Exercise

1. Add `JsonFormatter` to the triage module from Module 03.
2. Run `python -m triage` and confirm the log output is valid JSON.
3. Add a `latency_ms` field to every log line.
4. Sketch (in plain text or a diagram) what alerts you would set up based on
   your risk register from Module 01.
