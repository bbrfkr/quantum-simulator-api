from fastapi.testclient import TestClient

from ...main import app

client = TestClient(app)


def test_list_state(use_test_db, create_state):
    response = client.get("/state")
    assert response.status_code == 200
    assert str(create_state) in response.json()["states"]


def test_get_state(use_test_db, create_state):
    response = client.get(f"/state/{create_state}")
    assert response.status_code == 200
