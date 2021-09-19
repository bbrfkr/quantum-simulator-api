from math import sqrt

import pytest

from ..models.models import TransformerType


@pytest.fixture(
    scope="function",
    params=[
        {"type": TransformerType.OBSERVE, "matrix": [[1, 0], [0, 0]]},
        {
            "type": TransformerType.TIMEEVOLVE,
            "matrix": [[sqrt(1 / 2), sqrt(1 / 2)], [sqrt(1 / 2), -sqrt(1 / 2)]],
        },
    ],
)
def valid_transformer(request):
    return request.param
