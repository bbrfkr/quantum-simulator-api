import asyncio
import os
from math import sqrt

import pytest
from dotenv import load_dotenv
from fastapi_contrib.conf import settings
from fastapi_contrib.db.utils import setup_mongodb
from pymongo import MongoClient

from ...main import app
from ...models.models import State, Transformer, TransformerType

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
async def create_state(event_loop):
    qubit = [[1, 0], [0, 0]]
    register = [0]
    state_id = await State(qubits=qubit, registers=register).save()
    return state_id


@pytest.fixture(scope="function")
async def create_transformer(event_loop):
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
