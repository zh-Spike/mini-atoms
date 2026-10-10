from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz() -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_index_renders() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "mini-atoms" in resp.text
