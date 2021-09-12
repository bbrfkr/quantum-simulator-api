FROM python:3.9
COPY . /quantum-simulator-api
WORKDIR /quantum-simulator-api
RUN pip install .
CMD ["uvicorn", "quantum_simulator_api.main:app", "--host", "0.0.0.0"]
