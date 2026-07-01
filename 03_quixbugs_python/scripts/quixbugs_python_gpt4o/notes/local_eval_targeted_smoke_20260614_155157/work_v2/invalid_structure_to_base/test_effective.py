import pytest

sut = __import__("quixbugs_python_sut", fromlist=[""])
sut.to_base(5, 2)
