#!/usr/bin/env python3
from pathlib import Path
import ast
import importlib.util
import sys

root = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "projetos" / "SUTs" / "quixbugs"

suts = sorted(
    p for p in root.iterdir()
    if p.is_dir() and p.name[:3].isdigit() and "_python_" in p.name
)

bad = 0
print("sut_id\thas_sut_py\tcompile_ok\timport_ok\ttop_level_functions\terror")

for d in suts:
    sut_py = d / "sut.py"
    has = sut_py.is_file()
    compile_ok = False
    import_ok = False
    funcs = []
    err = ""

    try:
        if not has:
            raise FileNotFoundError("sut.py missing")

        src = sut_py.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src, filename=str(sut_py))
        funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        compile(src, str(sut_py), "exec")
        compile_ok = True

        old_path = list(sys.path)
        old_mod = sys.modules.pop("sut", None)
        try:
            sys.path.insert(0, str(d))
            spec = importlib.util.spec_from_file_location("sut", sut_py)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["sut"] = mod
            spec.loader.exec_module(mod)
            import_ok = True
        finally:
            sys.path[:] = old_path
            sys.modules.pop("sut", None)
            if old_mod is not None:
                sys.modules["sut"] = old_mod

    except Exception as e:
        err = f"{type(e).__name__}: {e}".replace("\n", " ")
        bad += 1

    print(f"{d.name}\t{int(has)}\t{int(compile_ok)}\t{int(import_ok)}\t{','.join(funcs)}\t{err}")

if bad:
    raise SystemExit(f"invalid_suts={bad}")
