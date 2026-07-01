#!/usr/bin/env bash
set -euo pipefail

cat <<'PY'
import sut

def test_single_digit():
    assert sut.next_palindrome([9]) == [1, 0, 1]

def test_two_digits():
    assert sut.next_palindrome([1, 2]) == [1, 3]

def test_three_digits():
    assert sut.next_palindrome([1, 2, 3]) == [1, 3, 1]

def test_four_digits():
    assert sut.next_palindrome([1, 2, 3, 4]) == [1, 3, 3, 1]

def test_edge_cases():
    assert sut.next_palindrome([1, 0, 0, 0, 1]) == [1, 0, 0, 1, 1]
PY
