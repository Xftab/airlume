"""Experiment A: the sandbox for model-written SQL and Python.

Model output is treated as hostile. These tests try the usual ways out: other
statements, files, extensions, imports, attribute tricks, names assembled at run
time, secrets in the environment, and endless loops.
"""
import duckdb
import pandas as pd
import pytest

from airlume.eval.expA import sandbox
from airlume.eval.expA.sandbox import check_python, check_sql, child_env, run_python, run_sql

NOW = "2026-11-20 12:00:00"


@pytest.fixture(scope="module")
def tables(tmp_path_factory):
    d = tmp_path_factory.mktemp("expA-tables")
    for name, text in sandbox._TINY.items():
        (d / name).write_text(text, encoding="utf-8")
    con = duckdb.connect(str(d / "analysis.duckdb"))
    for name in sandbox._TINY:
        con.register("incoming", pd.read_csv(d / name))
        con.execute(f"CREATE TABLE {name[:-4]} AS SELECT * FROM incoming")  # name from a fixed dict
        con.unregister("incoming")
    con.close()
    return d


# --------------------------------------------------------------------------- SQL

@pytest.mark.parametrize("sql", [
    "DROP TABLE city_hourly", "INSERT INTO city_hourly VALUES ('X', NULL, 1, 1, 1)",
    "SELECT 1; DROP TABLE city_hourly", "PRAGMA database_list", "ATTACH 'x.db' AS x",
    "COPY city_hourly TO 'out.csv'", "SET enable_external_access = true", "CALL pragma_version()",
    "INSTALL httpfs", "LOAD httpfs", "CREATE TABLE t AS SELECT 1", "UPDATE city_hourly SET aqi = 0",
    "EXPORT DATABASE 'dump'", "", "   ",
])
def test_only_one_select_is_allowed(sql):
    assert check_sql(sql) is not None


@pytest.mark.parametrize("sql", [
    "SELECT 1", "WITH x AS (SELECT 1 AS v) SELECT v FROM x",
    "SELECT city AS place, avg(aqi) AS value, 'aqi' AS unit FROM city_hourly GROUP BY city",
])
def test_selects_pass_the_check(sql):
    assert check_sql(sql) is None


def test_select_runs_read_only(tables):
    r = run_sql("SELECT city AS place, aqi AS value, 'aqi' AS unit FROM city_hourly", tables / "analysis.duckdb")
    assert r.ok and r.columns == ["place", "value", "unit"] and r.value == [["Lahore", 230, "aqi"]]


@pytest.mark.parametrize("sql", [
    "SELECT * FROM read_csv('stations.csv')", "SELECT * FROM read_text('stations.csv')",
    "SELECT * FROM glob('*')", "SELECT * FROM 'stations.csv'", "SELECT * FROM read_parquet('x.parquet')",
])
def test_files_are_out_of_reach_from_a_select(tables, sql):
    r = run_sql(sql, tables / "analysis.duckdb")
    assert not r.ok and r.blocked is None, r


def test_sql_errors_and_timeouts_are_reported(tables):
    r = run_sql("SELECT no_such_column FROM city_hourly", tables / "analysis.duckdb")
    assert not r.ok and "no_such_column" in r.error
    r = run_sql("SELECT count(*) FROM range(1000000000000) a", tables / "analysis.duckdb", timeout_s=2)
    assert r.timed_out


# --------------------------------------------------------------------------- Python, before running

@pytest.mark.parametrize("code", [
    "import os", "import subprocess", "from os import system", "import pandas.io.common",
    "from pandas import read_csv", "from numpy import *", "from numpy.lib import npyio", "from . import x",
    "open('x').read()", "eval('1')", "exec('x=1')", "getattr(pd, 'read_csv')", "__import__('os')",
    "x = ().__class__.__bases__", "station_hourly.to_csv('x.csv')", "pd.read_csv('x.csv')",
    "np.save('x', [1])", "np.load('x.npy')", "station_hourly.query('aqi > 1')", "pd.eval('1+1')",
    "pd.io.common", "np.lib.format", "np.ctypeslib", "x = pd.os", "station_hourly.agg('to_csv', 0, 'x.csv')",
    "'{0.gi_frame}'.format(x)", "y = '__class__'", "station_hourly.style", "vars()", "type(x).mro()",
    "pd.show_versions(as_json='x.json')", "station_hourly.to_string('x.txt')",
])
def test_disallowed_python_is_blocked_before_running(code):
    assert check_python(code) is not None, code


@pytest.mark.parametrize("code", [
    "s = station_hourly[station_hourly['station'] == 'GT Road']\n"
    "result = {'status': 'answer', 'place': 'GT Road', 'value': float(s['aqi'].iloc[-1]), 'unit': 'aqi'}",
    "import math\nfrom datetime import timedelta\nstart = NOW.normalize() - timedelta(days=7)\n"
    "m = city_hourly[(city_hourly['city'] == 'Lahore') & (city_hourly['ts_local'] >= start)]['aqi'].mean()\n"
    "result = {'status': 'answer' if not math.isnan(m) else 'no_data', 'place': 'Lahore', 'value': m, 'unit': 'aqi'}",
    "g = station_hourly.groupby('station')['aqi'].agg(['mean', 'max']).reset_index()\n"
    "top = g.sort_values('mean', ascending=False).iloc[0]\n"
    "result = {'status': 'answer', 'place': top['station'], 'value': top['mean'], 'unit': 'aqi'}",
    "df = pd.merge(stations, station_hourly, on=['station', 'city'], suffixes=('_s', '_h'))\nresult = None",
    "print(f'{NOW:%Y-%m-%d}', round(3.14159, 2))\nresult = None",
])
def test_ordinary_analysis_code_passes_the_check(code):
    assert check_python(code) is None, check_python(code)


# --------------------------------------------------------------------------- Python, running

def test_python_runs_and_returns_result(tables):
    r = run_python("s = station_hourly[station_hourly['station'] == 'GT Road']\n"
                   "result = {'status': 'answer', 'place': 'GT Road', 'value': s['aqi'].iloc[-1], 'unit': 'aqi'}\n"
                   "print('debug output is captured, not mixed with the result')",
                   tables, NOW)
    assert r.ok, r.error
    assert r.value == {"status": "answer", "place": "GT Road", "value": 240, "unit": "aqi"}
    assert "debug output" in r.stdout


def test_names_assembled_at_run_time_still_cannot_touch_files(tables, tmp_path):
    target = tmp_path / "leak.csv"
    code = f"station_hourly.agg('to_' + 'csv', 0, r'{target}')\nresult = None"
    r = run_python(code, tables, NOW)
    assert not r.ok and "PermissionError" in r.error
    assert not target.exists()
    r = run_python("f = getattr\nresult = 1", tables, NOW)
    assert r.blocked                                    # checked before running
    r = run_python("x = __builtins__\nresult = 1", tables, NOW)
    assert r.blocked


def test_runtime_import_hook_and_reduced_builtins(tables):
    # Assembled module names pass the source check; the import hook refuses them.
    r = run_python("import importlib\nresult = 1", tables, NOW)
    assert r.blocked
    r = run_python("m = 'o' + 's'\nresult = len(m)", tables, NOW)
    assert r.ok and r.value == 2                        # building a string is harmless on its own
    r = run_python("result = repr(station_hourly.head(1))", tables, NOW)
    assert r.ok and "GT Road" in r.value               # printing a frame still works


def test_child_sees_no_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_not_a_real_key")
    monkeypatch.setenv("WAQI_TOKEN", "test-token")
    env = child_env(tmp_path)
    assert "GROQ_API_KEY" not in env and "WAQI_TOKEN" not in env
    assert all(k in sandbox._ENV_ALLOW or k in ("TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE", "OPENBLAS_NUM_THREADS",
                                                 "OMP_NUM_THREADS", "MKL_NUM_THREADS") for k in env)


def test_sql_cannot_read_the_environment(tables, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_not_a_real_key")
    r = run_sql("SELECT getenv('GROQ_API_KEY') AS v", tables / "analysis.duckdb")
    assert not r.ok or r.value in ([[None]], [[""]])


def test_endless_python_is_stopped(tables):
    r = run_python("while True:\n    pass", tables, NOW, timeout_s=3)
    assert r.timed_out and not r.ok


def test_selftest_reports_on_this_machine():
    out = sandbox.selftest()
    assert out["python_runs"] and out["sql_runs"], out
    assert out["string_dispatch_refused"] and out["sql_file_access_refused"], out
    assert out["blocks_import_os"] and out["blocks_drop_table"]


# --------------------------------------------------------------------------- the whole surface

_ESCAPE_MODULES = {"os", "posix", "nt", "sys", "subprocess", "shutil", "socket", "builtins", "importlib", "ctypes",
                   "io", "_io", "pathlib", "pickle", "marshal", "inspect", "types", "enum", "functools", "operator",
                   "linecache", "tokenize", "codecs", "logging", "traceback", "pkgutil", "runpy", "code", "gc",
                   "weakref", "threading", "multiprocessing", "tempfile", "glob", "posixpath", "ntpath", "zipfile"}
_ESCAPE_FUNCS = {"open", "exec", "eval", "__import__", "getattr", "setattr", "delattr", "globals", "locals", "vars",
                 "input", "breakpoint", "system", "popen", "remove", "unlink", "rmtree", "getline", "attrgetter",
                 "methodcaller", "getmembers", "getattr_static", "currentframe", "_getframe"}


def test_no_route_from_allowed_modules_to_files_processes_or_code():
    """Walk every attribute path (five hops) the checker would let through, from each allowed
    module, and fail on any module or function that gives file, process or code access.
    On 20 Nov 2026 this found re.enum.bltns (the builtins module: open, exec) and
    numpy.char.overrides.inspect (getmembers); both are now blocked by name."""
    import importlib
    import types
    import warnings

    found = []
    for root in sorted(sandbox.ALLOWED_MODULES):
        mod = importlib.import_module(root)
        seen, frontier = {id(mod)}, [(mod, root)]
        for _ in range(5):
            nxt = []
            for obj, path in frontier:
                for name in dir(obj):
                    if sandbox.FORBIDDEN_ATTR.match(name):
                        continue
                    try:
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            v = getattr(obj, name)
                    except Exception:  # noqa: BLE001 - some attributes raise on access; they are not routes
                        continue
                    if isinstance(v, types.ModuleType):
                        parts = v.__name__.split(".")
                        if parts[0] in _ESCAPE_MODULES or parts[-1] in _ESCAPE_MODULES:
                            found.append(f"{path}.{name} -> {v.__name__}")
                        if id(v) not in seen:
                            seen.add(id(v))
                            nxt.append((v, f"{path}.{name}"))
                    elif callable(v) and not isinstance(v, type):
                        fmod = (getattr(v, "__module__", None) or "").split(".")[0]
                        if getattr(v, "__name__", "") in _ESCAPE_FUNCS and fmod not in ("numpy", "pandas"):
                            found.append(f"{path}.{name} -> {fmod}.{v.__name__}")
            frontier = nxt
    assert found == []
