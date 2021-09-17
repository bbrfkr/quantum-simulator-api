import logging
import random
from enum import IntEnum, auto
from math import sqrt
from typing import Dict, List, Optional

import quantum_simulator.channel.channel as qc
import quantum_simulator.channel.registers as qr
import quantum_simulator.channel.state as qs
from fastapi import FastAPI, HTTPException
from fastapi_contrib.db.models import MongoDBModel
from fastapi_contrib.db.utils import setup_mongodb
from fastapi_contrib.serializers import openapi
from fastapi_contrib.serializers.common import ModelSerializer
from pydantic import Field
from quantum_simulator.base.observable import Observable
from quantum_simulator.base.pure_qubits import PureQubits
from quantum_simulator.base.qubits import Qubits
from quantum_simulator.base.time_evolution import TimeEvolution
from quantum_simulator.channel.transformer import (
    ObserveTransformer,
    TimeEvolveTransformer,
)

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


@openapi.patch
class TransformerSerializer(ModelSerializer):
    def validate_matrix(self):
        try:
            matrix = [list(map(complex, row)) for row in self.matrix]
        except Exception:
            raise HTTPException(
                status_code=400, detail="given matrix cannot convert to complex matrix"
            )

        if self.type == TransformerType.OBSERVE:
            try:
                Observable(matrix)
            except Exception:
                raise HTTPException(
                    status_code=400, detail="given matrix is not observable"
                )
        if self.type == TransformerType.TIMEEVOLVE:
            try:
                TimeEvolution(matrix)
            except Exception:
                raise HTTPException(
                    status_code=400, detail="given matrix is not time evolution"
                )

    class Meta:
        model = Transformer


class State(MongoDBModel):
    qubits: List[List[str]]
    registers: List[int]

    class Meta:
        collection = "state"


class Channel(MongoDBModel):
    name: str = ""
    qubit_count: int = Field(1, ge=1, le=8)
    register_count: int = Field(1, ge=1, le=8)
    init_transformer_ids: List[int] = []
    state_ids: List[int] = []
    transformer_ids: List[int] = []
    outcome: Optional[int] = None

    class Meta:
        collection = "channel"


@openapi.patch
class ChannelSerializer(ModelSerializer):
    state_ids: List[int]
    transformer_ids: List[int]
    outcome: Optional[int]

    class Meta:
        model = Channel
        read_only_fields = {"state_ids", "transformer_ids", "outcome"}


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
async def create_channel(serializer: ChannelSerializer):
    channel = await serializer.save()
    return {"id": channel.id}


@app.delete("/channel/{id}", response_model=Dict[str, str])
async def delete_channel(id: int):
    channel = await Channel.get(id=id)
    if not channel:
        raise HTTPException(status_code=404, detail="not found")

    for state_id in channel.state_ids:
        await State.delete(id=state_id)

    await Channel.delete(id=id)
    return {"message": "deleted"}


@app.put("/channel/{id}/initialize", response_model=Dict[str, str])
async def initialize_state_of_channel(id: int):
    channel = await Channel.get(id=id)
    if not channel:
        raise HTTPException(
            status_code=404, detail=f"channel with id '{id}' is not found"
        )

    if len(channel.state_ids) > 0:
        raise HTTPException(
            status_code=400, detail=f"channel with id '{id}' is already initialized"
        )

    if channel.outcome:
        raise HTTPException(status_code=400, detail="this channel is already finalized")

    init_transformers = []
    for transformer_id in channel.init_transformer_ids:
        transformer = await Transformer.get(id=transformer_id)
        try:
            if transformer.type == TransformerType.OBSERVE:
                qc_transformer = ObserveTransformer(
                    Observable([list(map(complex, row)) for row in transformer.matrix])
                )
            elif transformer.type == TransformerType.TIMEEVOLVE:
                qc_transformer = TimeEvolveTransformer(
                    TimeEvolution(
                        [list(map(complex, row)) for row in transformer.matrix]
                    )
                )
        except Exception:
            raise HTTPException(
                status_code=400, detail="cannot convert matrix to transformer"
            )
        init_transformers.append(qc_transformer)

    qc_channel = qc.Channel(
        qubit_count=channel.qubit_count,
        register_count=channel.register_count,
        init_transformers=init_transformers,
    )
    try:
        qc_channel.initialize()
    except Exception:
        raise HTTPException(status_code=400, detail="cannot initialize channel")

    qubits = qc_channel.states[0].qubits.matrix.astype(str).tolist()
    registers = qc_channel.states[0].registers.values
    state_id = await State(qubits=qubits, registers=registers).save()
    try:
        await Channel.update_one(
            filter_kwargs={"id": channel.id},
            **{
                "$set": {
                    "state_ids": [state_id],
                }
            },
        )
    except Exception:
        await State.delete(id=state_id)
        raise HTTPException(status_code=500, detail="failed to update channel")

    return {"message": "initialized"}


@app.put("/channel/{id}/transform", response_model=Dict[str, str])
async def apply_transformer_to_channel(
    id: int, transformer_id: int, register_index: Optional[int] = None
):
    # get channel
    channel = await Channel.get(id=id)
    if not channel:
        raise HTTPException(
            status_code=404, detail=f"channel with id '{id}' is not found"
        )

    qc_channel = qc.Channel(
        qubit_count=channel.qubit_count,
        register_count=channel.register_count,
        init_transformers=[],
    )

    # check whether channel is finalized
    if channel.outcome:
        raise HTTPException(status_code=400, detail="this channel is already finalized")

    # get transformer. then set transformer to channel
    transformer = await Transformer.get(id=transformer_id)
    if not transformer:
        raise HTTPException(
            status_code=404,
            detail=f"transformer with id '{transformer_id}' is not found",
        )
    try:
        if transformer.type == TransformerType.OBSERVE:
            qc_transformer = ObserveTransformer(
                Observable([list(map(complex, row)) for row in transformer.matrix])
            )
        elif transformer.type == TransformerType.TIMEEVOLVE:
            qc_transformer = TimeEvolveTransformer(
                TimeEvolution([list(map(complex, row)) for row in transformer.matrix])
            )
    except Exception:
        raise HTTPException(
            status_code=400, detail="cannot convert matrix to transformer"
        )
    channel.transformer_ids.append(transformer_id)

    # get previous state. then set the state to channel
    try:
        pre_state = await State.get(id=channel.state_ids[-1])
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="this channel is not initialized",
        )
    qc_registers = qr.Registers(len(pre_state.registers))
    for index, value in enumerate(pre_state.registers):
        qc_registers.put(index, value)
    qc_qubits = Qubits([list(map(complex, row)) for row in pre_state.qubits])
    qc_state = qs.State(qc_qubits, qc_registers)
    qc_channel.states = [qc_state]

    # transform!!
    qc_channel.transform(qc_transformer, register_index)

    # append post state to channel
    post_qubits = qc_channel.states[-1].qubits.matrix.astype(str).tolist()
    post_registers = qc_channel.states[-1].registers.values
    post_state_id = await State(qubits=post_qubits, registers=post_registers).save()
    channel.state_ids.append(post_state_id)

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
    except Exception:
        await State.delete(id=post_state_id)
        raise HTTPException(status_code=500, detail="failed to update channel")

    return {"message": "transformed"}


@app.put("/channel/{id}/finalize", response_model=Dict[str, str])
async def finalize_channel(id: int, output_indices: List[int] = None):
    # get channel
    channel = await Channel.get(id=id)
    if not channel:
        raise HTTPException(
            status_code=404, detail=f"channel with id '{id}' is not found"
        )
    qc_channel = qc.Channel(
        qubit_count=channel.qubit_count,
        register_count=channel.register_count,
        init_transformers=[],
    )

    # check whether channel is finalized
    if channel.outcome:
        raise HTTPException(status_code=400, detail="this channel is already finalized")

    # get previous state. then set the state to channel
    try:
        pre_state = await State.get(id=channel.state_ids[-1])
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="this channel is not initialized",
        )
    qc_registers = qr.Registers(len(pre_state.registers))
    for index, value in enumerate(pre_state.registers):
        qc_registers.put(index, value)
    qc_qubits = Qubits([list(map(complex, row)) for row in pre_state.qubits])
    qc_state = qs.State(qc_qubits, qc_registers)
    qc_channel.states = [qc_state]

    # finalize!!
    qc_channel.finalize(output_indices)

    # append post state and outcome to channel
    post_qubits = qc_channel.states[-1].qubits.matrix.astype(str).tolist()
    post_registers = qc_channel.states[-1].registers.values
    post_state_id = await State(qubits=post_qubits, registers=post_registers).save()
    channel.state_ids.append(post_state_id)
    channel.outcome = qc_channel.outcome

    try:
        await Channel.update_one(
            filter_kwargs={"id": channel.id},
            **{"$set": {"state_ids": channel.state_ids, "outcome": channel.outcome}},
        )
    except Exception:
        await State.delete(id=post_state_id)
        raise HTTPException(status_code=500, detail="failed to update channel")

    return {"message": "finalized"}


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
async def create_transformer(serializer: TransformerSerializer):
    serializer.validate_matrix()
    transformer = await serializer.save()
    return {"id": transformer.id}


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
