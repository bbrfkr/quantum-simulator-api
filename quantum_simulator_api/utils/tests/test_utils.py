from ..utils import (
    remove_spaces,
    translate_imaginary_string,
    translate_imaginary_symbol,
)


def test_remove_spaces(matrix_includes_space):
    result_matrix = remove_spaces(matrix_includes_space)
    for row in result_matrix:
        for element in row:
            assert element == "1"


def test_translate_imaginary_string(matrix_includes_imaginary_string):
    result_matrix = translate_imaginary_string(matrix_includes_imaginary_string)
    for element in result_matrix:
        assert "j" in element


def test_translate_imaginary_symbol(matrix_includes_imaginary_symbol):
    result_matrix = translate_imaginary_symbol(matrix_includes_imaginary_symbol)
    for element in result_matrix:
        assert "i" in element
