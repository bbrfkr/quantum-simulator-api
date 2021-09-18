import random
from math import sqrt
from typing import Dict, List

from fastapi import APIRouter
from quantum_simulator.base.pure_qubits import PureQubits
from quantum_simulator.base.qubits import generalize

router = APIRouter(prefix="/channel", tags=["channel"])


# channel api
@router.get("/", response_model=Dict[str, List[str]])
async def list_channel():
    channels = await Channel.list()
    return {"channels": [channel["id"] for channel in channels]}


@router.get("/{id}", response_model=dict)
async def get_channel(id: int):
    channel = await Channel.get(id=id)
    if not channel:
        raise HTTPException(status_code=404, detail="not found")
    return channel


@router.post("/", response_model=Dict[str, str])
async def create_channel(serializer: ChannelSerializer):
    channel = await serializer.save()
    return {"id": channel.id}


@router.delete("/{id}", response_model=Dict[str, str])
async def delete_channel(id: int):
    channel = await Channel.get(id=id)
    if not channel:
        raise HTTPException(status_code=404, detail="not found")

    for state_id in channel.state_ids:
        await State.delete(id=state_id)

    await Channel.delete(id=id)
    return {"message": "deleted"}


@router.put("/{id}/initialize", response_model=Dict[str, str])
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

    if channel.outcome is not None:
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


@router.put("/{id}/transform", response_model=Dict[str, str])
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
    if channel.outcome is not None:
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


@router.put("/{id}/finalize", response_model=Dict[str, str])
async def finalize_channel(id: int, output_indices: List[int]):
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
    if channel.outcome is not None:
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
    channel.outcome = qc_channel.outcome.item()

    try:
        await Channel.update_one(
            filter_kwargs={"id": channel.id},
            **{"$set": {"state_ids": channel.state_ids, "outcome": channel.outcome}},
        )
    except Exception as e:
        await State.delete(id=post_state_id)
        logger.error(e)
        raise HTTPException(status_code=500, detail="failed to update channel")

    return {"message": "finalized"}