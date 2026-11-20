"""Run one model-written SQL query or Python snippet, locked down. Experiment A only.

The code and SQL arms are controls in an offline experiment; the app never runs
model-written code (design rule 1). Even here, model output is treated as hostile.

Both kinds
- run in a separate process started with ``python -I -X utf8`` (no user site, no
  PYTHON* variables), whose environment is built from an allow-list, so no API key
  or other secret is visible to it;
- the working directory is a fresh temporary folder, deleted afterwards;
- a wall-clock time limit kills the process;
- on Linux, when ``unshare`` is permitted, the process also gets no network
  (``unshare -rn``) and limits on memory and file size. On Windows neither is
  available, which the protocol records as a residual risk of running the arms on
  the laptop (protocol, section 7).

SQL
- exactly one statement, and DuckDB's own parser must classify it as SELECT;
- the database is opened read-only with external access disabled and the
  configuration locked, so files, extensions, ATTACH, COPY and SET all fail.

Python, checked before running (an AST allow-list)
- imports only from ALLOWED_MODULES, never ``*``, never a forbidden name or path;
- no forbidden names (open, eval, exec, getattr, __import__, ...), no attribute
  starting with "_", no file or system attribute (read_csv, to_csv, os, lib, io...);
- no text that spells a forbidden name ("to_csv"), because pandas looks some methods
  up by name (``df.agg("to_csv", ...)``), and no format field that reads attributes;
then executed with a reduced set of builtins, an import hook that repeats the
allow-list, and pandas and numpy file functions replaced by ones that refuse
(_py_runner.py), so a name assembled at run time still cannot write or read a file.

A refusal before running is reported as ``blocked`` with the reason; a refusal at
run time surfaces as a PermissionError. Scoring counts both as an attempted
disallowed action (protocol, section 6), not as a crash.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
SQL_RUNNER = HERE / "_sql_runner.py"
PY_RUNNER = HERE / "_py_runner.py"
# Temporary folders go under the repository's git-ignored cache, not the system temp folder:
# the laptop's C: drive is nearly full (CLAUDE.md), and each Python run copies the tables.
TMP_ROOT = HERE.parents[2] / "data" / "cache" / "expA" / "tmp"

SQL_TIMEOUT_S = 15
PY_TIMEOUT_S = 30
MAX_CODE_CHARS = 20_000
MAX_ROWS = 200

ALLOWED_MODULES = frozenset({
    "pandas", "numpy", "math", "statistics", "datetime", "collections", "itertools", "re", "zoneinfo",
})
FORBIDDEN_NAMES = frozenset({
    "open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr",
    "setattr", "delattr", "input", "breakpoint", "help", "exit", "quit", "memoryview", "dir",
    "type", "object", "super", "classmethod", "staticmethod", "property", "__builtins__",
    "__loader__", "__spec__", "os", "sys", "subprocess", "socket", "shutil", "pathlib", "io",
    "builtins", "importlib", "ctypes", "pickle", "marshal", "inspect", "requests", "urllib",
})
# Module names that lead to files, processes or code execution. Blocked as attribute and
# import names: the standard library is full of indirect routes (re.enum.bltns is the
# builtins module, numpy.char.overrides.inspect has getmembers), and
# tests/test_expA_sandbox.py walks every allowed module to prove none is left open.
_FORBIDDEN_MODULES = (
    "os", "posix", "nt", "posixpath", "ntpath", "genericpath", "sys", "subprocess", "shutil", "socket", "ssl",
    "http", "urllib", "builtins", "bltns", "importlib", "imp", "pkgutil", "zipimport", "runpy", "site", "sysconfig",
    "platform", "ctypes", "ctypeslib", "io", "pathlib", "glob", "fnmatch", "tempfile", "fileinput", "filecmp",
    "linecache", "tokenize", "codecs", "pickle", "marshal", "shelve", "dbm", "copyreg", "zipfile", "tarfile", "gzip",
    "bz2", "lzma", "sqlite3", "mmap", "signal", "threading", "multiprocessing", "concurrent", "asyncio", "selectors",
    "select", "resource", "gc", "weakref", "inspect", "dis", "ast", "symtable", "code", "codeop", "types", "enum",
    "functools", "operator", "abc", "warnings", "traceback", "logging", "faulthandler", "tracemalloc", "trace", "pdb",
    "bdb", "atexit", "webbrowser", "pty", "readline", "rlcompleter", "unittest", "doctest", "pydoc", "netrc",
    "plistlib", "configparser", "mailbox", "mimetypes",
    # pandas and numpy paths to the above or to native code
    "lib", "core", "compat", "util", "utils", "api", "testing", "distutils", "f2py", "common", "internals",
    "plotting", "modules", "overrides",
)
# File input and output and code evaluation, by method name. Also refused as plain text,
# because pandas looks some methods up by name: df.agg("to_csv", 0, "x.csv").
_IO_WORDS = (
    r"read_\w+|to_(csv|parquet|pickle|sql|excel|json|html|feather|hdf|stata|clipboard|xml|orc|latex"
    r"|string|markdown|gbq)"
    r"|eval|query|tofile|fromfile|fromregex|save|savez|savez_compressed|savetxt|load|loadtxt|genfromtxt"
    r"|memmap|dump|dumps|DataSource|ExcelFile|ExcelWriter|HDFStore|show_versions|system|popen"
)
# Introspection and indirect routes, by attribute name only.
_ATTR_WORDS = (
    r"load_library|style|plot|format_map|currentframe|getmembers|getattr_static|attrgetter|methodcaller"
    r"|(gi|f|co|tb|cr|ag)_\w+|"
    # "compile" stays allowed as an attribute: re.compile is harmless, and the builtin
    # compile is reachable only through names blocked here (builtins, bltns).
    + "|".join(sorted(set(_FORBIDDEN_MODULES) | set(FORBIDDEN_NAMES) - {"__builtins__", "__loader__",
                                                                    "__spec__", "__import__", "compile"}))
)
FORBIDDEN_ATTR = re.compile(rf"^(_.*|{_IO_WORDS}|{_ATTR_WORDS})$")
FORBIDDEN_TEXT = re.compile(rf"^({_IO_WORDS})$")
FORMAT_ATTR = re.compile(r"\{[^{}]*\.[A-Za-z_]")  # "{0.attr}".format(x) reads attributes
_LEADING = re.compile(r"^(?:\s|\(|--[^\n]*(?:\n|$)|/\*.*?\*/)*", re.S)  # whitespace, brackets, comments

# Environment variables the child may see. Everything else, keys included, is dropped.
_ENV_ALLOW = ("PATH", "SYSTEMROOT", "SystemRoot", "WINDIR", "COMSPEC", "LANG", "LC_ALL")


@dataclass
class ExecResult:
    ok: bool
    value: object = None              # python: the `result` object; sql: list of row lists
    columns: list[str] | None = None  # sql only
    error: str | None = None          # it ran and failed (or produced no usable output)
    blocked: str | None = None        # refused before running: an attempted disallowed action
    timed_out: bool = False
    seconds: float = 0.0
    stdout: str = ""
    extra: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- checks

def check_sql(sql: str | None) -> str | None:
    """Reason to refuse this SQL before running it, or None when it may run."""
    if not sql or not str(sql).strip():
        return "empty query"
    if len(sql) > MAX_CODE_CHARS:
        return "query too long"
    con = duckdb.connect(":memory:")
    try:
        statements = con.extract_statements(sql)
    except duckdb.Error:
        return None  # a syntax error is an ordinary failure; running it reports the error
    finally:
        con.close()
    if len(statements) != 1:
        return f"{len(statements)} statements; exactly one SELECT is allowed"
    st = statements[0]
    if st.type != duckdb.StatementType.SELECT:
        return f"statement type {st.type.name} is not allowed"
    # DuckDB rewrites PRAGMA, SHOW, DESCRIBE and SUMMARIZE into SELECTs; the contract is a
    # query that starts with SELECT or WITH (or DuckDB's FROM-first form), nothing else.
    head = _LEADING.sub("", sql, count=1)
    word = re.match(r"[A-Za-z]+", head)
    if not word or word.group(0).lower() not in ("select", "with", "from"):
        return f"the query must start with SELECT or WITH, not {(word.group(0) if word else head[:10])!r}"
    return None


class _Checker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.problems: list[str] = []

    def _module_path(self, dotted: str) -> None:
        parts = dotted.split(".")
        if parts[0] not in ALLOWED_MODULES:
            self.problems.append(f"import {dotted}")
        for seg in parts[1:]:
            if FORBIDDEN_ATTR.match(seg):
                self.problems.append(f"import path {dotted}")

    def visit_Import(self, node: ast.Import) -> None:
        for a in node.names:
            self._module_path(a.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level:
            self.problems.append("relative import")
        self._module_path(node.module or "")
        for a in node.names:
            if a.name == "*":
                self.problems.append(f"from {node.module} import *")
            elif a.name in FORBIDDEN_NAMES or FORBIDDEN_ATTR.match(a.name):
                self.problems.append(f"from {node.module} import {a.name}")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in FORBIDDEN_NAMES or node.id.startswith("__"):
            self.problems.append(f"name {node.id}")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if FORBIDDEN_ATTR.match(node.attr):
            self.problems.append(f"attribute .{node.attr}")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        v = node.value
        if isinstance(v, str):
            if "__" in v:
                self.problems.append("text containing '__'")
            if FORBIDDEN_TEXT.match(v.strip()):
                self.problems.append(f"text {v.strip()!r} names a forbidden method")
            if FORMAT_ATTR.search(v):
                self.problems.append("format field reading an attribute")
        self.generic_visit(node)


def check_python(code: str | None) -> str | None:
    """Reason to refuse this Python before running it, or None when it may run."""
    if not code or not str(code).strip():
        return "empty code"
    if len(code) > MAX_CODE_CHARS:
        return "code too long"
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None  # an ordinary failure; running it reports the error
    c = _Checker()
    c.visit(tree)
    if c.problems:
        return "; ".join(sorted(set(c.problems)))[:300]
    return None


# --------------------------------------------------------------------------- process

def child_env(tmp: Path) -> dict[str, str]:
    """The child's whole environment: an allow-list, plus a private temp folder."""
    env = {k: os.environ[k] for k in _ENV_ALLOW if k in os.environ}
    env.update({"TEMP": str(tmp), "TMP": str(tmp), "TMPDIR": str(tmp), "HOME": str(tmp),
                "USERPROFILE": str(tmp), "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1"})
    return env


@lru_cache(maxsize=1)
def _no_network_prefix() -> tuple[str, ...]:
    """('unshare', '-rn') when this machine lets an unprivileged process drop the network."""
    if sys.platform != "linux" or not shutil.which("unshare"):
        return ()
    try:
        r = subprocess.run(["unshare", "-rn", "true"], capture_output=True, timeout=5)
        return ("unshare", "-rn") if r.returncode == 0 else ()
    except (OSError, subprocess.SubprocessError):
        return ()


def network_isolated() -> bool:
    return bool(_no_network_prefix())


def _limits() -> None:  # pragma: no cover - runs in the child on POSIX only
    import resource
    two_gb = 2 * 1024 ** 3
    resource.setrlimit(resource.RLIMIT_AS, (two_gb, two_gb))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 ** 2, 10 * 1024 ** 2))


def _run_child(runner: Path, payload: dict, timeout_s: int, cwd: Path) -> tuple[dict | None, bool, float]:
    cmd = [*_no_network_prefix(), sys.executable, "-I", "-X", "utf8", str(runner)]
    t0 = time.time()
    try:
        r = subprocess.run(
            cmd, input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout_s, cwd=str(cwd), env=child_env(cwd),
            preexec_fn=_limits if os.name == "posix" else None,
        )
    except subprocess.TimeoutExpired:
        return None, True, time.time() - t0
    secs = time.time() - t0
    out = (r.stdout or "").strip().splitlines()
    for line in reversed(out):
        if line.startswith("{"):
            try:
                return json.loads(line), False, secs
            except ValueError:
                break
    return {"ok": False, "error": ("no result printed; " + (r.stderr or "")[-500:]).strip()}, False, secs


def run_sql(sql: str | None, db_path: Path, timeout_s: int = SQL_TIMEOUT_S,
            max_rows: int = MAX_ROWS) -> ExecResult:
    reason = check_sql(sql)
    if reason:
        return ExecResult(ok=False, blocked=reason)
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="expA-sql-", dir=TMP_ROOT) as tmp:
        payload = {"sql": sql, "db": str(Path(db_path).resolve()), "max_rows": max_rows}
        out, timed_out, secs = _run_child(SQL_RUNNER, payload, timeout_s, Path(tmp))
    if timed_out:
        return ExecResult(ok=False, error=f"timed out after {timeout_s} s", timed_out=True, seconds=secs)
    if not out.get("ok"):
        return ExecResult(ok=False, error=str(out.get("error"))[:500], seconds=secs)
    return ExecResult(ok=True, value=out["rows"], columns=out["columns"], seconds=secs,
                      extra={"truncated": out.get("truncated", False)})


def run_python(code: str | None, tables_dir: Path, now_local: str,
               timeout_s: int = PY_TIMEOUT_S) -> ExecResult:
    reason = check_python(code)
    if reason:
        return ExecResult(ok=False, blocked=reason)
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="expA-py-", dir=TMP_ROOT) as tmp:
        tmp_path = Path(tmp)
        data = tmp_path / "data"
        data.mkdir()
        for f in Path(tables_dir).glob("*.csv"):
            shutil.copy2(f, data / f.name)
        payload = {"code": code, "tables_dir": "data", "now_local": now_local,
                   "allowed_modules": sorted(ALLOWED_MODULES),
                   "forbidden_attr": FORBIDDEN_ATTR.pattern}
        out, timed_out, secs = _run_child(PY_RUNNER, payload, timeout_s, tmp_path)
    if timed_out:
        return ExecResult(ok=False, error=f"timed out after {timeout_s} s", timed_out=True, seconds=secs)
    if not out.get("ok"):
        return ExecResult(ok=False, error=str(out.get("error"))[:500], seconds=secs,
                          stdout=str(out.get("stdout", ""))[:1000])
    return ExecResult(ok=True, value=out.get("result"), seconds=secs, stdout=str(out.get("stdout", ""))[:1000])


# --------------------------------------------------------------------------- self-test

_TINY = {
    "stations.csv": "station,city,lat,lon\nGT Road,Lahore,31.58,74.36\n",
    "cities.csv": "city,province\nLahore,Punjab\n",
    "areas.csv": "area,lat,lon,city\nModel Town,31.48,74.32,Lahore\n",
    "station_hourly.csv": "station,city,ts_local,pm25,pm10,aqi\nGT Road,Lahore,2026-11-20 11:00:00,150.0,250.0,240\n",
    "city_hourly.csv": "city,ts_local,pm25,pm10,aqi\nLahore,2026-11-20 11:00:00,140.0,240.0,230\n",
    "forecast.csv": "city,issued_local,target_local,aqi,source\nLahore,2026-11-20 11:00:00,2026-11-20 12:00:00,250,EPA Punjab\n",
}


def selftest() -> dict:
    """What the sandbox can and cannot do on this machine (no model, no real data)."""
    out = {"network_isolated": network_isolated(), "platform": sys.platform}
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="expA-selftest-", dir=TMP_ROOT) as tmp:
        d = Path(tmp)
        for name, text in _TINY.items():
            (d / name).write_text(text, encoding="utf-8")
        ok = run_python("x = station_hourly[station_hourly['station'] == 'GT Road']['aqi'].iloc[-1]\n"
                        "result = {'status': 'answer', 'place': 'GT Road', 'value': float(x), 'unit': 'aqi'}",
                        d, "2026-11-20 12:00:00")
        out["python_runs"] = ok.ok and (ok.value or {}).get("value") == 240.0
        out["python_error"] = ok.error
        dispatch = run_python("station_hourly.agg('to_' + 'csv', 0, 'leak.csv')\nresult = None", d,
                              "2026-11-20 12:00:00")
        out["string_dispatch_refused"] = (not dispatch.ok) and "PermissionError" in (dispatch.error or "")
        con = duckdb.connect(str(d / "t.duckdb"))
        con.execute("CREATE TABLE city_hourly AS SELECT 'Lahore' AS city, 230 AS aqi")
        con.close()
        q = run_sql("SELECT city AS place, aqi AS value, 'aqi' AS unit FROM city_hourly", d / "t.duckdb")
        out["sql_runs"] = q.ok and q.value == [["Lahore", 230, "aqi"]]
        f = run_sql("SELECT * FROM read_csv('stations.csv')", d / "t.duckdb")
        out["sql_file_access_refused"] = (not f.ok) and f.blocked is None
    out["blocks_import_os"] = check_python("import os") is not None
    out["blocks_drop_table"] = check_sql("DROP TABLE x") is not None
    return out
