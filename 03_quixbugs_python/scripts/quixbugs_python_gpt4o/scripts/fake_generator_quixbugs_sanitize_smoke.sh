#!/usr/bin/env bash
set -euo pipefail

PROMPT_FILE="${1:?usage: fake_generator_quixbugs_sanitize_smoke.sh PROMPT_FILE}"

cat <<'PY'
import sut

def test_bitcount_zero():
    assert sut.bitcount(0) == 0

def test_bitcount_one():
    assert sut.bitcount(1) == 1

def test_bitcount_power_of_two():
    assert sut.bitcount(8) == 1

def test_bitcount_multiple_bits():
    assert sut.bitcount(7) == 3

def test_bitcount_large_value():
    assert sut.bitcount(255) == 8

def test_bitcount_intentionally_wrong_for_sanitizer():
    assert sut.bitcount(7) == 999
PY
