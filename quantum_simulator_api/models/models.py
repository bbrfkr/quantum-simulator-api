from enum import IntEnum, auto
from fastapi_contrib.db.models import MongoDBModel
from typing import List, Optional
from pydantic import Field


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
    qubit_count: int = Field(1, ge=1, le=8)
    register_count: int = Field(1, ge=1, le=8)
    init_transformer_ids: List[int] = []
    state_ids: List[int] = []
    transformer_ids: List[int] = []
    outcome: Optional[int] = None

    class Meta:
        collection = "channel"


