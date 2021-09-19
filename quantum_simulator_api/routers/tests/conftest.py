import asyncio
import os

import pytest
from dotenv import load_dotenv
from fastapi_contrib.conf import settings
from fastapi_contrib.db.utils import setup_mongodb
from pymongo import MongoClient

from quantum_simulator_api.main import app
from quantum_simulator_api.models.models import State

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
