import asyncio

from fastapi.testclient import TestClient

from ...main import app
from ...models.models import Transformer

client = TestClient(app)


def test_list_transformer(use_test_db, create_transformer):
    response = client.get("/transformer/")
    assert response.status_code == 200
    assert str(create_transformer) in response.json()["transformers"]


def test_get_transformer(use_test_db, create_transformer):
    response = client.get(f"/transformer/{create_transformer}")
    assert response.status_code == 200


def test_create_transformer(use_test_db, transformer_params):
    event_loop = asyncio.get_event_loop()
    response = client.post("/transformer/", json=transformer_params)
    transformer = event_loop.run_until_complete(
        Transformer.get(id=int(response.json()["id"]))
    )
    assert response.status_code == 200
    assert transformer.type == transformer_params["type"]
    assert transformer.name == transformer_params["name"]

    comparison_matrix = [list(map(str, row)) for row in transformer_params["matrix"]]
    assert transformer.matrix == comparison_matrix
