# QueueStorm Investigator

QueueStorm Investigator is a FastAPI backend for the SUST CSE Carnival 2026 Codex Community Hackathon preliminary challenge. By default it runs as an offline, deterministic rule-based investigator. It reads a support complaint and the supplied recent transaction history, then returns an evidence-backed routing decision for support staff.

It is an internal support copilot, not an autonomous financial decision maker. It does not connect to bKash or any real payment system.

## API

Only two public routes are enabled:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Returns `{"status":"ok"}`. |
| `POST` | `/analyze-ticket` | Returns one structured ticket analysis. |

Example request:

```json
{
  "ticket_id": "TKT-001",
  "complaint": "I sent 5000 taka to a wrong number around 2pm today.",
  "language": "en",
  "transaction_history": [
    {
      "transaction_id": "TXN-9101",
      "timestamp": "2026-04-14T14:08:22Z",
      "type": "transfer",
      "amount": 5000,
      "counterparty": "+8801719876543",
      "status": "completed"
    }
  ]
}
```

The response always includes `ticket_id`, `relevant_transaction_id`, `evidence_verdict`, `case_type`, `severity`, `department`, `agent_summary`, `recommended_next_action`, `customer_reply`, `human_review_required`, `confidence`, and `reason_codes`. See [samples/sample-output.json](samples/sample-output.json) for a generated response.

## Run locally

Requires Python 3.12+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then call the service:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/analyze-ticket -Method Post -ContentType 'application/json' -InFile samples/sample-request.json
```

`POST /analyze-ticket` returns controlled JSON errors: malformed JSON or missing required fields return `400`; semantic validation failures such as blank complaints or invalid enums return `422`.

## Docker fallback

```powershell
docker build -t queuestorm-investigator .
docker run --rm -p 8000:8000 --env-file .env.example queuestorm-investigator
```

The image uses `python:3.12-slim`, binds Uvicorn to `0.0.0.0:8000`, has no GPU requirement, and has no network/API-key dependency when `LLM_ENABLED=false`.

## Tests

```powershell
pytest -q
python scripts/test_samples.py
```

The local pack contains ten public-case calibrations. It checks the important decision fields and customer-reply safety; it does not hardcode responses into the analyzer.

## Reasoning design

The service keeps deterministic rules as the source of truth:

1. It normalizes English/Bangla digits and text, extracts amounts, transaction IDs, phones, and approximate time.
2. It scans for credential-risk, phishing/social-engineering, and prompt-injection signals before financial case types.
3. It extracts rule-based facts and checks rule confidence.
4. If confidence is low and `LLM_ENABLED=true`, an optional Gemini extractor may fill missing facts only. It cannot decide the case type, evidence verdict, severity, department, review policy, or final text.
5. It scores provided transactions using explicit IDs, amount, expected transaction type, recipient, time, and recency.
6. It returns `insufficient_data` instead of guessing where multiple candidates are equally plausible.
7. It applies case-specific evidence policies, routes to the correct department, derives severity/review status, and generates a concise safe response.

| Case type | Department |
| --- | --- |
| `wrong_transfer` | `dispute_resolution` |
| `payment_failed`, `duplicate_payment` | `payments_ops` |
| `merchant_settlement_delay` | `merchant_operations` |
| `agent_cash_in_issue` | `agent_operations` |
| `phishing_or_social_engineering` | `fraud_risk` |
| `refund_request`, `other` | `customer_support` unless the refund is contested |

## Safety logic

- The service never asks customers for a PIN, OTP, password, secret code, or full card number.
- It never promises a refund, reversal, account unblock, recovery, or direct financial action. Eligible outcomes are described as being handled through official channels.
- It does not follow instructions embedded in a complaint. Optional AI is limited to fact extraction, is disabled by default, and fails back to deterministic rules.
- A final guard scans generated summaries, actions, and replies for unsafe credential requests, promises, and suspicious third-party contact instructions before returning the response.

## Optional AI fact extraction

AI is not required to run the service. To enable the low-confidence fact-extraction fallback, set these environment variables outside the repo:

```powershell
$env:LLM_ENABLED = "true"
$env:GEMINI_API_KEY = "<temporary-key-from-private-env>"
$env:GEMINI_MODEL = "gemini-2.5-flash"
```

Do not commit real keys. If the key is missing, the package is unavailable, the model times out, or the model returns invalid JSON, the API returns the deterministic rule-based result.

## Limitations

- This is a rule-based prototype; unfamiliar wording, incomplete histories, and complex real-world disputes may need human review.
- It only reasons from the current request and supplied transaction snippet; it has no live ledger, account, or merchant-policy access.
- Bangla handling is keyword/template based and is designed for the preliminary synthetic cases, not comprehensive natural-language understanding.

## Submission checklist

- [x] Required endpoints and exact enum values implemented.
- [x] Offline rule-based operation by default; optional AI fact extraction is fail-safe.
- [x] Docker fallback and documented run command included.
- [x] Sample request, generated sample response, and public-case test script included.
- [x] No real customer data, real payment integrations, or secrets included.
- [x] `.env.example` contains placeholders only.
