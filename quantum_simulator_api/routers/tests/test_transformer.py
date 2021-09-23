import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from ...main import app
from ...models.models import Transformer
from ..transformer import check_channel_dependency

client = TestClient(app)


def test_list_transformer(use_test_db, create_transformer):
    response = client.get("/transformer/")
    assert response.status_code == 200
    assert create_transformer in [
        transformer["id"] for transformer in response.json()["transformers"]
    ]


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


def test_delete_transformer(use_test_db, create_transformer):
    response = client.delete(f"/transformer/{create_transformer}")
    assert response.status_code == 200

    list_response = client.get("/transformer/")
    assert str(create_transformer) not in list_response.json()["transformers"]

    response = client.delete(f"/transformer/{create_transformer}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_check_channel_dependency(
    use_test_db, create_channel_with_init_transformer, create_channel_with_transformer
):
    with pytest.raises(HTTPException):
        await check_channel_dependency(
            create_channel_with_init_transformer["init_transformer_id"]
        )

    with pytest.raises(HTTPException):
        await check_channel_dependency(
            create_channel_with_transformer["transformer_id"]
        )
