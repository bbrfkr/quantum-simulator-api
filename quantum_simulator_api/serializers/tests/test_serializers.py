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


def test_invalidate_matrix(invalid_transformer):
    serializer = TransformerSerializer(
        type=invalid_transformer["type"], matrix=invalid_transformer["matrix"]
    )
    with pytest.raises(Exception):
        serializer.validate_matrix()
