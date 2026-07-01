import pytest
from sut import bitcount

def test_bitcount():
    assert bitcount(0) == 0
    assert bitcount(1) == 1
    assert bitcount(2) == 1
    assert bitcount(3) == 2
    assert bitcount(4) == 1
    assert bitcount(5) == 2
    assert bitcount(6) == 2
    assert bitcount(7) == 3
    assert bitcount(8) == 1
    assert bitcount(9) == 2
    assert bitcount(10) == 2
    assert bitcount(15) == 4
    assert bitcount(31) == 5
    assert bitcount(63) == 6

def test_bitcount_edge_cases():
    with pytest.raises(ValueError):
        bitcount(-1)

def test_bitcount_random_inputs():
    for _ in range(100):
        n = random.randint(0, 2**32-1)
        count = bitcount(n)
        assert count == len(list(bin(n).split('0b')[2])) - 1
