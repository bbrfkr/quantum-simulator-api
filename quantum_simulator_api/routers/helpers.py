import random
from math import sqrt
from typing import Dict, List

from fastapi import APIRouter
from quantum_simulator.base.pure_qubits import PureQubits
from quantum_simulator.base.qubits import generalize

router = APIRouter(prefix="", tags=["helpers"])


# helper api
@router.get("/healthz")
def health_check():
    return {"message": "healthy"}


@router.get("/random", response_model=Dict[str, List[List[float]]])
def get_random_pure_qubit():
    amp = random.random()
    qubit = generalize(PureQubits([sqrt(amp), sqrt(1 - amp)]))
    return {"qubit": qubit.matrix.tolist()}
