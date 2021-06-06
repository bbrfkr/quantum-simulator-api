from fastapi import FastAPI
from quantum_simulator.base.pure_qubits import PureQubits
import random
from math import sqrt

app = FastAPI()


@app.get("/")
def get_root():
    return {"Hello": "World"}


@app.get("/random")
def get_random():
    amp = random.random()
    qubit = PureQubits([sqrt(amp), sqrt(1 - amp)])
    return {"qubit": str(list(qubit.vector)) }
