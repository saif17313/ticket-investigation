"""``GET /health`` must return exactly ``{"status": "ok"}`` with 200."""

from __future__ import annotations


def test_health_returns_exact_spec_shape(client) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body == {"status": "ok"}
    assert set(body.keys()) == {"status"}