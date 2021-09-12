from fastapi import FastAPI, HTTPException
from quantum_simulator.base.pure_qubits import PureQubits
import random
from quantum_simulator.base.observable import Observable
from quantum_simulator.base.time_evolution import TimeEvolution
from math import sqrt
from typing import List, Dict
from fastapi_contrib.db.utils import setup_mongodb
from fastapi_contrib.db.models import MongoDBModel
import logging
from enum import IntEnum, auto

logger = logging.getLogger("uvicorn")

app = FastAPI()


# models
class TransformerType(IntEnum):
    OBSERVE = auto()
    TIMEEVOLVE = auto()


class Transformer(MongoDBModel):
    type: TransformerType
    name: str = ""
    matrix: List[List[str]]

    class Meta:
        collection = "transformer"


class State(MongoDBModel):
    qubits: List[List[str]]
    registers: List[int]

    class Meta:
        collection = "state"


class Channel(MongoDBModel):
    name: str = ""
    qubit_count: int
    register_count: int
    init_transformer_ids: List[int] = []
    transformer_ids: List[int] = []
    state_ids: List[int] = []

    class Meta:
        collection = "channel"


# setup
@app.on_event("startup")
async def startup():
    setup_mongodb(app)


# utils
def check_complex_str(target: str):
    try:
        complex(target)
    except Exception as e:
        logger.warn(e)
        raise


# helper api
@app.get("/healthz")
def health():
    return {"message": "healthy"}


@app.get("/random", response_model=Dict[str, str])
def random_qubit():
    amp = random.random()
    qubit = PureQubits([sqrt(amp), sqrt(1 - amp)])
    return {"qubit": str(list(qubit.vector))}


# channel api
@app.get("/channel/", response_model=Dict[str, List[str]])
async def list_channel():
    channels = await Channel.list()
    return {"channels": [channel["id"] for channel in channels]}


@app.get("/channel/{id}", response_model=dict)
async def get_channel(id: int):
    channel = await Channel.get(id=id)
    if not channel:
        raise HTTPException(status_code=404, detail="not found")
    return channel


@app.post("/channel/", response_model=Dict[str, str])
async def create_channel(channel: Channel):
    id = await channel.save()
    return {"id": id}


@app.delete("/channel/{id}", response_model=Dict[str, str])
async def delete_channel(id: int):
    channel = await Channel.get(id=id)
    if not channel:
        raise HTTPException(status_code=404, detail="not found")

    for state_id in channel.state_ids:
        await State.delete(id=state_id)

    await Channel.delete(id=id)
    return {"message": "deleted"}


@app.put("/channel/{id}/transform", response_model=Dict[str, str])
async def apply_transformer_to_channel(id: int, transformer_id: int):
    channel = await Channel.get(id=id)
    if not channel:
        raise HTTPException(
            status_code=404, detail=f"channel with id '{id}' is not found"
        )

    transformer = await Transformer.get(id=transformer_id)
    if not transformer:
        raise HTTPException(
            status_code=404,
            detail=f"transformer with id '{transformer_id}' is not found",
        )

    channel.transformer_ids.append(transformer_id)

    # TODO: calculate applied state
    state = State(qubits=[], registers=[])
    state_id = await state.save()
    channel.state_ids.append(state_id)

    try:
        await Channel.update_one(
            filter_kwargs={"id": channel.id},
            **{
                "$set": {
                    "transformer_ids": channel.transformer_ids,
                    "state_ids": channel.state_ids,
                }
            },
        )
    except Exception as e:
        await State.delete(id=state_id)
        logger.error(e)
        raise HTTPException(status_code=500, detail="failed to update channel")

    return {"message": "transformed"}


# transformer api
@app.get("/transformer/", response_model=Dict[str, List[str]])
async def list_transformer():
    transformers = await Transformer.list()
    return {"transformers": [transformer["id"] for transformer in transformers]}


@app.get("/transformer/{id}", response_model=dict)
async def get_transformer(id: int):
    transformer = await Transformer.get(id=id)
    if not transformer:
        raise HTTPException(status_code=404, detail="not found")
    return transformer


@app.post("/transformer/", response_model=Dict[str, str])
async def create_transformer(transformer: Transformer):
    try:
        matrix = [list(map(complex, row)) for row in transformer.matrix]
    except Exception:
        raise HTTPException(
            status_code=400, detail="given matrix cannot convert to complex matrix"
        )

    if transformer.type == TransformerType.OBSERVE:
        try:
            Observable(matrix)
        except Exception:
            raise HTTPException(
                status_code=400, detail="given matrix is not observable"
            )
    if transformer.type == TransformerType.TIMEEVOLVE:
        try:
            TimeEvolution(matrix)
        except Exception:
            raise HTTPException(
                status_code=400, detail="given matrix is not time evolution"
            )

    id = await transformer.save()
    return {"id": id}


@app.delete("/transformer/{id}", response_model=Dict[str, str])
async def delete_transformer(id: int):
    transformer = await Transformer.get(id=id)
    if not transformer:
        raise HTTPException(status_code=404, detail="not found")
    for channel in await Channel.list():
        if (
            id in channel["init_transformer_ids"]
            or transformer in channel["transformer_ids"]
        ):
            raise HTTPException(
                status_code=400,
                detail=f"this transformer is used by channel id {channel['id']}",
            )
    await Transformer.delete(id=id)
    return {"message": "deleted"}


# state api
@app.get("/state/", response_model=Dict[str, List[str]])
async def list_state():
    states = await State.list()
    return {"states": [state["id"] for state in states]}


@app.get("/state/{id}", response_model=dict)
async def get_state(id: int):
    state = await State.get(id=id)
    if not state:
        raise HTTPException(status_code=404, detail="not found")
    return state