from math import sqrt

import pytest

from ..models.models import TransformerType


@pytest.fixture(
    scope="function",
    params=[
        {"type": TransformerType.OBSERVE, "matrix": [["1", "0j"], ["0", "0"]]},
        {
            "type": TransformerType.TIMEEVOLVE,
            "matrix": [
                [str(sqrt(1 / 2)), str(sqrt(1 / 2))],
                [str(sqrt(1 / 2)), str(-sqrt(1 / 2))],
            ],
        },
    ],
)
def valid_transformer(request):
    return request.param


@pytest.fixture(
    scope="function",
    params=[
        {"type": TransformerType.OBSERVE, "matrix": [["1", "0i"], ["0", "0"]]},
        {"type": TransformerType.OBSERVE, "matrix": [["1ERROR", "0"], ["0", "0"]]},
        {
            "type": TransformerType.TIMEEVOLVE,
            "matrix": [["1", "0"], ["0", "0"]],
        },
    ],
)
def invalid_transformer(request):
    return request.param
