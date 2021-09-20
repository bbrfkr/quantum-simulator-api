import asyncio
import os
from math import sqrt

import pytest
from dotenv import load_dotenv
from fastapi_contrib.conf import settings
from fastapi_contrib.db.utils import setup_mongodb
from pymongo import MongoClient

from ...main import app
from ...models.models import Channel, State, Transformer, TransformerType

# set fastapi contrib config for test
load_dotenv(f"{os.getcwd()}/.env")
settings.mongodb_dsn = os.environ["PYTEST_MONGODB_DSN"]
settings.mongodb_dbname = os.environ["PYTEST_MONGODB_DBNAME"]
settings.fastapi_app = os.environ["PYTEST_FASTAPI_APP"]
setup_mongodb(app)


@pytest.fixture(scope="function")
def use_test_db():
    yield
    cleanup_client = MongoClient(settings.mongodb_dsn)
    cleanup_client.drop_database(settings.mongodb_dbname)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def create_state():
    qubit = [[1, 0], [0, 0]]
    register = [0]
    state_id = await State(qubits=qubit, registers=register).save()
    return state_id


@pytest.fixture(scope="function")
async def create_transformer():
    transformer_type = TransformerType.TIMEEVOLVE
    name = "test time evolve transformer"
    matrix = [[sqrt(1 / 2), sqrt(1 / 2)], [sqrt(1 / 2), -sqrt(1 / 2)]]
    transformer_id = await Transformer(
        type=transformer_type, name=name, matrix=matrix
    ).save()
    return transformer_id


@pytest.fixture(scope="function")
async def transformer_params():
    transformer_type = TransformerType.OBSERVE
    name = "test observe transformer"
    matrix = [[1, 0], [0, 0]]
    body = {"type": transformer_type, "name": name, "matrix": matrix}
    return body


@pytest.fixture(scope="function")
async def create_channel_with_init_transformer(create_transformer):
    name = "test channel with init transformer"
    init_transformer_ids = [create_transformer]
    channel_id = await Channel(
        name=name, init_transformer_ids=init_transformer_ids
    ).save()
    return {"channel_id": channel_id, "init_transformer_id": create_transformer}


@pytest.fixture(scope="function")
async def create_channel_with_transformer(create_transformer):
    name = "test channel with transformer"
    transformer_ids = [create_transformer]
    channel_id = await Channel(name=name, transformer_ids=transformer_ids).save()
    return {"channel_id": channel_id, "transformer_id": create_transformer}
