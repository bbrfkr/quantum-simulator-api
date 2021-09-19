import pytest

from ..serializers import TransformerSerializer


def test_validate_matrix(valid_transformer):
    serializer = TransformerSerializer(
        type=valid_transformer["type"], matrix=valid_transformer["matrix"]
    )
    try:
        serializer.validate_matrix()
    except Exception:
        pytest.fail("valid matrix is dealed with invalid")
