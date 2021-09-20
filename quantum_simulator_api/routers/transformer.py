from typing import Dict, List

from fastapi import APIRouter, HTTPException

from ..models.models import Channel, Transformer
from ..serializers.serializers import TransformerSerializer

router = APIRouter(prefix="/transformer", tags=["transformer"])


# transformer api
@router.get("/", response_model=Dict[str, List[str]])
async def list_transformer():
    transformers = await Transformer.list()
    return {"transformers": [transformer["id"] for transformer in transformers]}


@router.get("/{id}", response_model=dict)
async def get_transformer(id: int):
    transformer = await Transformer.get(id=id)
    if not transformer:
        raise HTTPException(status_code=404, detail="not found")
    return transformer


@router.post("/", response_model=Dict[str, str])
async def create_transformer(serializer: TransformerSerializer):
    serializer.validate_matrix()
    transformer = await serializer.save()
    return {"id": transformer.id}


@router.delete("/{id}", response_model=Dict[str, str])
async def delete_transformer(id: int):
    transformer = await Transformer.get(id=id)
    if not transformer:
        raise HTTPException(status_code=404, detail="not found")
    await check_channel_dependency(id)

    await Transformer.delete(id=id)
    return {"message": "deleted"}


async def check_channel_dependency(transformer_id: int) -> None:
    for channel in await Channel.list():
        if (
            transformer_id in channel["init_transformer_ids"]
            or transformer_id in channel["transformer_ids"]
        ):
            raise HTTPException(
                status_code=400,
                detail=f"this transformer is used by channel id {channel['id']}",
            )
