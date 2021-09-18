import pytest
from fastapi.testclient import TestClient
from quantum_simulator.base.qubits import Qubits

from quantum_simulator_api.main import app

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"message": "healthy"}


def test_random():
    response = client.get("/random")
    assert response.status_code == 200
    qubit_matrix = [list(map(float, row)) for row in response.json()["qubit"]]
    try:
        Qubits(qubit_matrix)
    except Exception:
        pytest.fail("generated matrix is not qubit")
