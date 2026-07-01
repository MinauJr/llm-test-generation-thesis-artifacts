import sut
from pytest import mark

@mark.parametrize("input,expected", [
    (0, 0),
    (1, 1),
    (2, 1),
    (3, 2),
    (4, 1),
    (5, 2),
    (6, 2),
    (7, 3),
    (8, 1),
    (9, 2),
    (10, 2),
    (11, 3),
    (12, 3),
    (13, 4),
    (14, 3),
    (15, 4),
    (16, 4),
])
def test_bitcount(input, expected):
    assert sut.bitcount(input) == expected
