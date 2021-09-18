from fastapi_contrib.serializers.common import ModelSerializer
from fastapi_contrib.serializers import openapi
from fastapi import HTTPException

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

@openapi.patch
class ChannelSerializer(ModelSerializer):
    state_ids: List[int]
    transformer_ids: List[int]
    outcome: Optional[int]

    class Meta:
        model = Channel
        read_only_fields = {"state_ids", "transformer_ids", "outcome"}
