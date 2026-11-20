"""Child process for sandbox.run_sql. Reads one JSON payload on stdin, prints one JSON line.

Started by sandbox.py with ``python -I`` in an empty temporary folder and a cleaned
environment. Not imported by anything; do not add imports beyond the standard
library and duckdb.
"""
import datetime
import decimal
import json
import sys

import duckdb


def _jsonable(v):
    if isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (bytes, bytearray)):
        return None
    return v


def main() -> None:
    p = json.loads(sys.stdin.read())
    try:
        con = duckdb.connect(p["db"], read_only=True, config={
            "enable_external_access": False,
            "autoinstall_known_extensions": False,
            "autoload_known_extensions": False,
            "lock_configuration": True,
            "threads": 1,
            "memory_limit": "512MB",
        })
        cur = con.execute(p["sql"])
        cols = [d[0] for d in (cur.description or [])]
        n = int(p.get("max_rows", 200))
        rows = cur.fetchmany(n + 1)
        out = {"ok": True, "columns": cols, "rows": [[_jsonable(v) for v in r] for r in rows[:n]],
               "truncated": len(rows) > n}
    except Exception as e:  # noqa: BLE001 - every failure is reported, never raised
        out = {"ok": False, "error": f"{type(e).__name__}: {e}"[:500]}
    print(json.dumps(out, default=str))


if __name__ == "__main__":
    main()
