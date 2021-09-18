from typing import Dict, List

from fastapi import APIRouter
from quantum_simulator_api.models.models import State
from fastapi import HTTPException

router = APIRouter(prefix="/state", tags=["state"])


# state api
@router.get("/", response_model=Dict[str, List[str]])
async def list_state():
    states = await State.list()
    return {"states": [state["id"] for state in states]}


@router.get("/{id}", response_model=dict)
async def get_state(id: int):
    state = await State.get(id=id)
    if not state:
        raise HTTPException(status_code=404, detail="not found")
    return state
