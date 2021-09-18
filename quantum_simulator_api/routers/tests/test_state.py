import pytest
from fastapi.testclient import TestClient

from quantum_simulator_api.main import app
from fastapi_contrib.db.utils import setup_mongodb
from fastapi_contrib.conf import settings
import os

client = TestClient(app)

def test_list_state(use_test_db, create_state):
    response = client.get("/state")
    assert response.status_code == 200
    assert str(create_state) in response.json()["states"]

def test_get_state(use_test_db, create_state):
    response = client.get(f"/state/{create_state}")
    assert response.status_code == 200
