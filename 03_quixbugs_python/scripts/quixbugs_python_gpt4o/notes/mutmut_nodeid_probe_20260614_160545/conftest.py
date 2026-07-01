import builtins
import importlib
import os
from pathlib import Path


try:
    builtins.sut = importlib.import_module("sut")
except Exception:
    pass


def pytest_collection_modifyitems(config, items):
    if os.environ.get("QUIXBUGS_EFFECTIVE_FILTER") != "1":
        return

    allow_file = Path(__file__).with_name("effective_nodeids.txt")

    if not allow_file.is_file():
        return

    allowed = {
        line.strip()
        for line in allow_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    selected = []
    deselected = []

    for item in items:
        if item.nodeid in allowed:
            selected.append(item)
        else:
            deselected.append(item)

    items[:] = selected

    if deselected:
        config.hook.pytest_deselected(items=deselected)
