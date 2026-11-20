"""Child process for sandbox.run_python. Reads one JSON payload on stdin, prints one JSON line.

Started by sandbox.py with ``python -I -X utf8`` in a temporary folder that holds only
copies of the snapshot tables, with a cleaned environment. The model's code has
already passed the parent's AST check; this file adds run-time layers:

- a reduced set of builtins (no open, eval, exec, getattr, __import__ of its own);
- an import hook that repeats the module allow-list, including the names imported;
- pandas and numpy file functions replaced, after the tables are loaded, by ones
  that refuse. pandas looks some methods up by name (``df.agg("to_csv", ...)``), and
  a name can be assembled at run time, which no check of the source can see.

Not imported by anything.
"""
import builtins
import contextlib
import datetime
import io
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

TABLES = ("stations", "cities", "areas", "station_hourly", "city_hourly", "forecast")
TIME_COLS = ("ts_local", "issued_local", "target_local")
SAFE = ("abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float", "format",
        "frozenset", "int", "isinstance", "len", "list", "map", "max", "min", "next", "pow",
        "print", "range", "repr", "reversed", "round", "set", "slice", "sorted", "str", "sum",
        "tuple", "zip", "ValueError", "KeyError", "IndexError", "TypeError", "ZeroDivisionError",
        "Exception", "StopIteration", "True", "False", "None")

_DENY_FRAME = ("to_pickle", "to_parquet", "to_excel", "to_hdf", "to_feather", "to_stata", "to_orc",
               "to_sql", "to_clipboard", "to_gbq", "eval", "query")
_BUFFER_FRAME = ("to_csv", "to_json", "to_string", "to_markdown", "to_html", "to_latex", "to_xml")
_DENY_PANDAS = ("to_pickle", "eval", "show_versions", "ExcelWriter", "ExcelFile", "HDFStore")
_DENY_NUMPY = ("save", "savez", "savez_compressed", "savetxt", "load", "loadtxt", "genfromtxt",
               "fromfile", "fromregex", "memmap")


def _deny(name):
    def refuse(*args, **kwargs):
        raise PermissionError(f"{name} is not allowed in the sandbox")
    return refuse


def _buffer_only(orig, name):
    """Allow writing to an in-memory string (what repr() does); refuse a path or a file."""
    def guarded(self, *args, **kwargs):
        target = args[0] if args else next(
            (kwargs[k] for k in ("buf", "path_or_buf", "path_or_buffer") if k in kwargs), None)
        if target is not None and not isinstance(target, io.StringIO):
            raise PermissionError(f"{name} to a file is not allowed in the sandbox")
        return orig(self, *args, **kwargs)
    return guarded


def lock_down_io() -> None:
    for cls in (pd.DataFrame, pd.Series):
        for name in _DENY_FRAME:
            if hasattr(cls, name):
                setattr(cls, name, _deny(f"{cls.__name__}.{name}"))
        for name in _BUFFER_FRAME:
            if hasattr(cls, name):
                setattr(cls, name, _buffer_only(getattr(cls, name), f"{cls.__name__}.{name}"))
    for name in dir(pd):
        if name.startswith("read_") or name in _DENY_PANDAS:
            setattr(pd, name, _deny(f"pandas.{name}"))
    for name in _DENY_NUMPY:
        if hasattr(np, name):
            setattr(np, name, _deny(f"numpy.{name}"))


def _jsonable(v):
    if v is None or isinstance(v, (bool, str)):
        return v
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(v, (pd.Timestamp, datetime.datetime, datetime.date)):
        return v.isoformat()
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, pd.Series):
        return _jsonable(v.tolist())
    if isinstance(v, pd.DataFrame):
        return _jsonable(v.head(50).to_dict(orient="records"))
    if isinstance(v, np.ndarray):
        return _jsonable(v.tolist())
    return str(v)[:200]


def main() -> None:
    p = json.loads(sys.stdin.read())
    allowed = set(p["allowed_modules"])
    forbidden = re.compile(p["forbidden_attr"])
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        parts = name.split(".")
        if level != 0 or parts[0] not in allowed or any(forbidden.match(s) for s in parts[1:]):
            raise ImportError(f"import of {name} is not allowed")
        for item in fromlist or ():
            if item == "*" or forbidden.match(item):
                raise ImportError(f"from {name} import {item} is not allowed")
        return real_import(name, globals, locals, fromlist, level)

    safe_builtins = {n: getattr(builtins, n) for n in SAFE if hasattr(builtins, n)}
    safe_builtins["__import__"] = guarded_import

    data = Path(p["tables_dir"])
    g = {"__builtins__": safe_builtins, "pd": pd, "np": np, "NOW": pd.Timestamp(p["now_local"])}
    for t in TABLES:
        df = pd.read_csv(data / f"{t}.csv")
        for c in TIME_COLS:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c])
        g[t] = df
    lock_down_io()

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(p["code"], "<model code>", "exec"), g)  # noqa: S102 - checked, reduced builtins, child process
        out = {"ok": True, "result": _jsonable(g.get("result")), "stdout": buf.getvalue()[-1000:]}
    except BaseException as e:  # noqa: BLE001 - every failure is reported, never raised
        out = {"ok": False, "error": f"{type(e).__name__}: {e}"[:500], "stdout": buf.getvalue()[-1000:]}
    print(json.dumps(out, default=str))


if __name__ == "__main__":
    main()
