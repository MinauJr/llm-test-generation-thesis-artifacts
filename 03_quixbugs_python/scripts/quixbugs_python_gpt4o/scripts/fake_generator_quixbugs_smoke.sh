#!/usr/bin/env bash
set -euo pipefail

PROMPT_FILE="${1:?usage: fake_generator_quixbugs_smoke.sh PROMPT_FILE}"

if grep -q "def bitcount" "$PROMPT_FILE"; then
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
PY
else
  cat <<'PY'
import sut

def test_smoke_imports_sut():
    assert sut is not None

def test_smoke_has_public_names():
    assert any(not name.startswith("_") for name in dir(sut))

def test_smoke_module_name():
    assert sut.__name__ == "sut"

def test_smoke_dict_exists():
    assert isinstance(sut.__dict__, dict)

def test_smoke_callable_or_class_exists():
    assert any(callable(v) for k, v in sut.__dict__.items() if not k.startswith("_"))
PY
fi
