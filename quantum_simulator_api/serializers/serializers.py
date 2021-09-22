from fastapi import HTTPException
from fastapi_contrib.serializers import openapi
from fastapi_contrib.serializers.common import ModelSerializer
from quantum_simulator.base.observable import Observable
from quantum_simulator.base.time_evolution import TimeEvolution

from ..models.models import Transformer, TransformerType


@openapi.patch
class TransformerSerializer(ModelSerializer):
    id: int

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
        read_only_fields = {"id"}
