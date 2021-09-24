from typing import List

def remove_spaces(matrix: List[List[str]]) -> List[List[str]]:
    return [
        list(map(lambda s: s.replace(" ", ""), row))
        for row in matrix
    ]

def translate_imaginary_string(matrix: List[List[str]]) -> List[List[str]]:
    return [
        list(map(lambda s: s.replace("j", "ERROR").replace("i", "j"), row))
        for row in matrix
    ]

def translate_imaginary_symbol(matrix: List[List[str]]) -> List[List[str]]:
    return [
        list(map(lambda s: s.replace("j", "i"), row))
        for row in matrix
    ]
