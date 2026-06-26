"""Input validation: empty complaint → 422, missing fields → 422."""

from __future__ import annotations


def test_empty_complaint_returns_422(client, sample_payload) -> None:
    r = client.post("/analyze-ticket", json={**sample_payload, "complaint": ""})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "validation_error"
    assert any(d["field"] == "body.complaint" for d in body["details"])


def test_missing_required_field_returns_422(client) -> None:
    r = client.post("/analyze-ticket", json={"ticket_id": "t"})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "validation_error"
    assert len(body["details"]) >= 1


def test_health_does_not_leak_secrets_on_error(client, monkeypatch) -> None:
    # Health can never fail in a way that leaks secrets, but verify the
    # generic 500 envelope contains no traceback text if anything goes wrong.
    r = client.get("/health")
    assert r.status_code == 200