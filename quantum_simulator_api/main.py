import logging
import os
from typing import Dict, List, Optional

import quantum_simulator.channel.channel as qc
import quantum_simulator.channel.registers as qr
import quantum_simulator.channel.state as qs
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi_contrib.db.models import MongoDBModel
from fastapi_contrib.db.utils import setup_mongodb
from fastapi_contrib.serializers import openapi
from fastapi_contrib.serializers.common import ModelSerializer
from pydantic import Field
from quantum_simulator.base.observable import Observable
from quantum_simulator.base.qubits import Qubits
from quantum_simulator.base.time_evolution import TimeEvolution
from quantum_simulator.channel.transformer import (
    ObserveTransformer,
    TimeEvolveTransformer,
)

from .models.models import State, Transformer, TransformerType
from .routers import helpers, state, transformer
from .utils.utils import (
    remove_spaces,
    translate_imaginary_string,
    translate_imaginary_symbol,
)

logger = logging.getLogger("uvicorn")

app = FastAPI()
app.include_router(helpers.router)
app.include_router(state.router)
app.include_router(transformer.router)

# cors settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("ALLOW_ORIGIN", "*")],
)


# models
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
    id: int
    state_ids: List[int]
    transformer_ids: List[int]
    outcome: Optional[int]

    class Meta:
        model = Channel
        read_only_fields = {"id", "state_ids", "transformer_ids", "outcome"}


# setup
@app.on_event("startup")
async def startup():
    setup_mongodb(app)


# channel api
@app.get("/channel/", response_model=Dict[str, List[Dict]])
async def list_channel():
    channels = await Channel.list()
    return {
        "channels": [
            {
                "id": channel["id"],
                "name": channel["name"],
            }
            for channel in channels
        ]
    }


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
        message = f"channel with id '{id}' is not found"
        logger.exception(message)
        raise HTTPException(status_code=404, detail=message)

    if len(channel.state_ids) > 0:
        message = f"channel with id '{id}' is already initialized"
        logger.exception(message)
        raise HTTPException(status_code=400, detail=message)

    if channel.outcome is not None:
        message = f"channel with id='{id}' is already finalized"
        logger.exception(message)
        raise HTTPException(status_code=400, detail=message)

    init_transformers = []
    for transformer_id in channel.init_transformer_ids:
        transformer = await Transformer.get(id=transformer_id)
        sanitized_matrix = translate_imaginary_string(remove_spaces(transformer.matrix))
        evaled_matrix = [
            list(map(lambda s: complex(eval(s)), row)) for row in sanitized_matrix
        ]
        try:
            if transformer.type == TransformerType.OBSERVE:
                qc_transformer = ObserveTransformer(Observable(evaled_matrix))
            elif transformer.type == TransformerType.TIMEEVOLVE:
                qc_transformer = TimeEvolveTransformer(TimeEvolution(evaled_matrix))
        except Exception as e:
            logger.exception(e)
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
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=400, detail="cannot initialize channel")

    qubits = translate_imaginary_symbol(
        qc_channel.states[0].qubits.matrix.astype(str).tolist()
    )
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
    except Exception as e:
        await State.delete(id=state_id)
        logger.exception(e)
        raise HTTPException(status_code=500, detail="failed to update channel")

    return {"message": "initialized", "state_id": state_id}


@app.put("/channel/{id}/transform", response_model=Dict[str, str])
async def apply_transformer_to_channel(
    id: int, transformer_id: int, register_index: Optional[int] = None
):
    # get channel
    channel = await Channel.get(id=id)
    if not channel:
        message = f"channel with id '{id}' is not found"
        logger.exception(message)
        raise HTTPException(status_code=404, detail=message)

    qc_channel = qc.Channel(
        qubit_count=channel.qubit_count,
        register_count=channel.register_count,
        init_transformers=[],
    )

    # check whether channel is finalized
    if channel.outcome is not None:
        message = f"channel with id '{id}' is already finalized"
        logger.exception(message)
        raise HTTPException(status_code=400, detail=message)

    # get transformer. then set transformer to channel
    transformer = await Transformer.get(id=transformer_id)
    if not transformer:
        message = f"transformer with id '{transformer_id}' is not found"
        logger.exception(message)
        raise HTTPException(
            status_code=404,
            detail=message,
        )

    sanitized_matrix = translate_imaginary_string(remove_spaces(transformer.matrix))
    evaled_matrix = [
        list(map(lambda s: complex(eval(s)), row)) for row in sanitized_matrix
    ]
    try:
        if transformer.type == TransformerType.OBSERVE:
            qc_transformer = ObserveTransformer(Observable(evaled_matrix))
        elif transformer.type == TransformerType.TIMEEVOLVE:
            qc_transformer = TimeEvolveTransformer(TimeEvolution(evaled_matrix))
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=400, detail="cannot convert matrix to transformer"
        )
    channel.transformer_ids.append(transformer_id)

    # get previous state. then set the state to channel
    try:
        pre_state = await State.get(id=channel.state_ids[-1])
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=400,
            detail="this channel is not initialized",
        )
    qc_registers = qr.Registers(len(pre_state.registers))
    for index, value in enumerate(pre_state.registers):
        qc_registers.put(index, value)

    qc_qubits = Qubits(
        [
            list(map(complex, row))
            for row in translate_imaginary_string(pre_state.qubits)
        ]
    )
    qc_state = qs.State(qc_qubits, qc_registers)
    qc_channel.states = [qc_state]

    # transform!!
    qc_channel.transform(qc_transformer, register_index)

    # append post state to channel
    post_qubits = translate_imaginary_symbol(
        qc_channel.states[-1].qubits.matrix.astype(str).tolist()
    )
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
    except Exception as e:
        await State.delete(id=post_state_id)
        logger.exception(e)
        raise HTTPException(status_code=500, detail="failed to update channel")

    return {
        "message": "transformed",
        "state_id": post_state_id,
    }


@app.put("/channel/{id}/finalize", response_model=Dict[str, str])
async def finalize_channel(id: int, output_indices: List[int]):
    # get channel
    channel = await Channel.get(id=id)
    if not channel:
        message = f"channel with id '{id}' is not found"
        logger.exception(message)
        raise HTTPException(status_code=404, detail=message)
    qc_channel = qc.Channel(
        qubit_count=channel.qubit_count,
        register_count=channel.register_count,
        init_transformers=[],
    )

    # check whether channel is finalized
    if channel.outcome is not None:
        message = f"channel with id={id} is already finalized"
        logger.exception(message)
        raise HTTPException(status_code=400, detail=message)

    # get previous state. then set the state to channel
    try:
        pre_state = await State.get(id=channel.state_ids[-1])
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=400,
            detail="this channel is not initialized",
        )
    qc_registers = qr.Registers(len(pre_state.registers))
    for index, value in enumerate(pre_state.registers):
        qc_registers.put(index, value)

    qc_qubits = Qubits(
        [
            list(map(complex, row))
            for row in translate_imaginary_string(pre_state.qubits)
        ]
    )
    qc_state = qs.State(qc_qubits, qc_registers)
    qc_channel.states = [qc_state]

    # finalize!!
    qc_channel.finalize(output_indices)

    # append post state and outcome to channel
    post_qubits = translate_imaginary_symbol(
        qc_channel.states[-1].qubits.matrix.astype(str).tolist()
    )
    post_registers = qc_channel.states[-1].registers.values
    post_state_id = await State(qubits=post_qubits, registers=post_registers).save()
    channel.state_ids.append(post_state_id)
    channel.outcome = qc_channel.outcome.item()

    try:
        await Channel.update_one(
            filter_kwargs={"id": channel.id},
            **{"$set": {"state_ids": channel.state_ids, "outcome": channel.outcome}},
        )
    except Exception as e:
        await State.delete(id=post_state_id)
        logger.exception(e)
        raise HTTPException(status_code=500, detail="failed to update channel")

    return {
        "message": "finalized",
        "state_id": post_state_id,
        "outcome": channel.outcome,
    }
