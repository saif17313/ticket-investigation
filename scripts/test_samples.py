"""Run the public calibration pack against the FastAPI application locally."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402

FIELDS_TO_COMPARE = (
    "relevant_transaction_id",
    "evidence_verdict",
    "case_type",
    "department",
    "severity",
    "human_review_required",
)
UNSAFE_REPLY_PATTERN = re.compile(
    r"\b(?:we will refund(?: you)?|we will reverse|guaranteed refund|send (?:your )?(?:otp|pin|password)|provide (?:your )?(?:otp|pin|password))\b",
    re.IGNORECASE,
)


def main() -> int:
    payload = json.loads((ROOT / "samples" / "sample-cases.json").read_text(encoding="utf-8"))
    client = TestClient(app)
    passed = 0
    for case in payload["cases"]:
        response = client.post("/analyze-ticket", json=case["input"])
        result = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        expected = case["expected_output"]
        failures: list[str] = []
        if response.status_code != 200:
            failures.append(f"status={response.status_code}")
        for field in FIELDS_TO_COMPARE:
            if result.get(field) != expected.get(field):
                failures.append(f"{field}: expected {expected.get(field)!r}, got {result.get(field)!r}")
        if UNSAFE_REPLY_PATTERN.search(result.get("customer_reply", "")):
            failures.append("customer_reply contains an unsafe request or promise")
        if failures:
            print(f"FAIL {case['id']}: {'; '.join(failures)}")
        else:
            print(f"PASS {case['id']}: {case['label']}")
            passed += 1
    print(f"\nSummary: {passed}/{len(payload['cases'])} cases passed")
    return 0 if passed == len(payload["cases"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
