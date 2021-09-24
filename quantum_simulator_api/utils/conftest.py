from math import sqrt

import pytest


@pytest.fixture(
    scope="function",
    params=[
        [
            [
                "1 ", "  1",
            ],
            [
                " 1  ", "1",
            ],
        ],
    ],
)
def matrix_includes_space(request):
    return request.param


@pytest.fixture(
    scope="function",
    params=[
        [
            "1j", "(-1)*j",
        ],
    ],
)
def matrix_includes_imaginary_symbol(request):
    return request.param


@pytest.fixture(
    scope="function",
    params=[
        [
            "1i", "(-1)*i",
        ],
    ],
)
def matrix_includes_imaginary_string(request):
    return request.param
