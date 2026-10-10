from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_unknown_api_route_is_404(client: TestClient) -> None:
    assert client.get("/api/nope").status_code == 404
