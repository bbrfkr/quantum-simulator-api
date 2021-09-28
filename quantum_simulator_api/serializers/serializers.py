import logging
from math import sqrt  # noqa

from fastapi import HTTPException
from fastapi_contrib.serializers import openapi
from fastapi_contrib.serializers.common import ModelSerializer
from quantum_simulator.base.observable import Observable
from quantum_simulator.base.time_evolution import TimeEvolution
from quantum_simulator.base.utils import count_bits

from ..models.models import Transformer, TransformerType

logger = logging.getLogger("uvicorn")


@openapi.patch
class TransformerSerializer(ModelSerializer):
    id: int
    target_qubit_count: int

    def validate_matrix(self):
        try:
            matrix = [list(map(lambda s: complex(eval(s)), row)) for row in self.matrix]
        except Exception as e:
            logger.exception(e)
            raise HTTPException(
                status_code=400, detail="given matrix cannot convert to complex matrix"
            )

        if self.type == TransformerType.OBSERVE:
            try:
                Observable(matrix)
            except Exception as e:
                logger.exception(e)
                raise HTTPException(
                    status_code=400, detail="given matrix is not observable"
                )
        if self.type == TransformerType.TIMEEVOLVE:
            try:
                TimeEvolution(matrix)
            except Exception as e:
                logger.exception(e)
                raise HTTPException(
                    status_code=400, detail="given matrix is not time evolution"
                )

    def get_target_qubit_count(self) -> int:
        return count_bits(len(self.matrix))

    class Meta:
        model = Transformer
        read_only_fields = {"id", "target_qubit_count"}
