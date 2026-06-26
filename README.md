# QueueStorm Investigator

Internal AI copilot for fintech customer support agents. Receives a customer
complaint together with recent transaction history and returns a structured
investigation result.

This repository contains the **backend service**. The rule engine and the
AI/Gemini module are plugged in via clean interfaces; a stub rule engine
ships by default so the API runs end-to-end out of the box.

---

## API

| Method | Path              | Purpose                                      |
|--------|-------------------|----------------------------------------------|
| GET    | `/health`         | Liveness probe → `{"status": "ok"}`          |
| POST   | `/analyze-ticket` | Run a full investigation, return structured JSON |

### Request schema (`POST /analyze-ticket`)

```jsonc
{
  "ticket_id": "T-1001",
  "complaint": "I sent 5000 to the wrong number yesterday",
  "language": "en",
  "channel": "app",
  "user_type": "retail",
  "campaign_context": "",
  "transaction_history": [
    {
      "transaction_id": "TX1001",
      "timestamp": "2025-01-01T00:00:00Z",
      "type": "transfer",
      "amount": 5000.0,
      "counterparty": "+8801712345678",
      "status": "completed"
    }
  ],
  "metadata": { "device": "android" }
}
```

### Response schema

The exact 12-field contract is enforced by Pydantic in
`app/schemas/response.py`. Any drift fails loudly. The enums (evidence
verdict, severity, case type, department) are locked to the values listed
in the specification.

### HTTP status codes

| Code | When                                                        |
|------|-------------------------------------------------------------|
| 200  | Successful analysis                                         |
| 400  | Malformed JSON or otherwise unparseable request             |
| 422  | Schema is syntactically valid but semantically invalid      |
| 500  | Unexpected server error (no stack traces, no secrets leaked) |

All error responses share a uniform envelope:

```json
{
  "code": "validation_error",
  "message": "The request body is invalid.",
  "details": [{ "field": "body.complaint", "message": "..." }]
}
```

---

## Project layout

```
app/
├── api/            # FastAPI routes + dependency providers
│   ├── analyze.py  #   POST /analyze-ticket
│   ├── health.py   #   GET /health
│   ├── router.py   #   central route registry
│   └── deps.py     #   FastAPI dependency providers (DI)
├── core/           # Cross-cutting concerns
│   ├── config.py   #   pydantic-settings Settings
│   ├── errors.py   #   centralized 400/422/500 handlers
│   └── logging.py  #   structured JSON logging
├── models/         # Internal domain models (not part of API)
│   └── decision.py #   InvestigationDecision
├── schemas/        # Public API contracts
│   ├── request.py  #   AnalyzeRequest + TransactionIn
│   ├── response.py #   AnalyzeResponse + enums
│   └── error.py    #   ErrorResponse envelope
├── services/       # Business logic + integrations
│   ├── rule_engine.py  #   RuleEngine Protocol + StubRuleEngine
│   ├── ai_service.py   #   AIService Protocol + Narrative
│   ├── gemini_service.py  #   [redacted] 2.5 Flash impl
│   └── investigator.py    #   Top-level orchestrator
├── utils/
│   └── safety.py   #   AI output safety filter
├── prompts/        # prompt templates (added in Step 10 if needed)
└── main.py         # FastAPI entrypoint
tests/              # pytest suite
samples/            # example payloads for manual curl testing
Dockerfile
docker-compose.yml
requirements.txt
.env.example
```

---

## Local development

### 1. Install dependencies

```powershell
pip install -r requirements.txt
```

### 2. Configure environment

```powershell
Copy-Item .env.example .env
# Edit .env if you have a Gemini API key
```

### 3. Run the server

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Try the endpoints

```powershell
# Health
curl http://localhost:8000/health

# Analyze
curl -X POST http://localhost:8000/analyze-ticket `
  -H "Content-Type: application/json" `
  -d "@samples/wrong_transfer.json"
```

---

## Docker

```powershell
docker build -t queuestorm-investigator .
docker run --env-file .env -p 8000:8000 queuestorm-investigator
# or
docker compose up --build
```

The image runs as a non-root user, exposes port 8000, and includes a
`HEALTHCHECK` against `/health`.

---

## Tests

```powershell
python -m pytest -q
```

The suite covers:

- `/health` returns exactly `{"status": "ok"}`
- Response schema has the exact 12 spec fields
- Enum allow-lists reject drift
- Empty complaint → 422 with safe envelope
- End-to-end `/analyze-ticket` happy path
- Safety filter strips OTP requests, refund promises, third-party links

---

## Configuration

All runtime configuration is read from environment variables (or a `.env`
file in development). See `app/core/config.py` and `.env.example` for the
full list.

| Variable                | Default               | Purpose                                  |
|-------------------------|-----------------------|------------------------------------------|
| `GEMINI_API_KEY`        | *(empty)*             | Required only if `LLM_ENABLED=true`      |
| `GEMINI_MODEL`          | `gemini-2.5-flash`    | Gemini model name                        |
| `LLM_ENABLED`           | `true`                | Set `false` for safe-mode templated text |
| `LLM_TIMEOUT_SECONDS`   | `8.0`                 | Hard timeout for Gemini calls            |
| `HIGH_VALUE_THRESHOLD`  | `10000`               | Used by the rule engine for severity     |
| `LOG_LEVEL`             | `INFO`                | One of DEBUG/INFO/WARNING/ERROR/CRITICAL |

---

## Architecture

```
HTTP request
   │
   ▼
Pydantic validation ──► 422 on invalid input
   │
   ▼
InvestigatorService
   │
   ├─► RuleEngine.decide(request)        # deterministic
   │      │
   │      └─► InvestigationDecision
   │
   ├─► AIService.narrate(request, decision) # narrative only
   │      │
   │      └─► Narrative (3 strings)
   │
   ├─► SafetyFilter.sanitize(narrative)   # last line of defense
   │
   ▼
AnalyzeResponse (locked to spec)
```

- The **rule engine** owns every decision field (transaction match,
  evidence verdict, case type, severity, department, human review).
- The **AI module** owns only the three narrative fields.
- The **safety filter** strips unsafe AI output as a final guarantee.
- **The backend never contains business reasoning.**

---

## Swapping in the real rule engine

Implement the `RuleEngine` Protocol in `app/services/rule_engine.py`:

```python
class RuleEngine(Protocol):
    def decide(self, request: AnalyzeRequest) -> InvestigationDecision: ...
```

Then in `app/api/deps.py` replace the `_rule_engine_singleton()` factory
with your implementation. No other file needs to change.

---

## Safety policy

The API never asks for, and the safety filter never allows, customer-facing
text that:

- requests an OTP, PIN, password, or card number
- promises a refund, reversal, account recovery, or account unblock
- directs the customer to a third-party link or handle

Any AI output that triggers these rules is replaced with a safe fallback
and `human_review_required` is forced to `true`.
