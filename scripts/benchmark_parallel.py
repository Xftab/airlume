r"""E5 (CC425 Parallel and Distributed Computing): speed-up of the EPD bulletin extraction.

    python scripts\benchmark_parallel.py --n 40 --repeats 1      # quick check, a few minutes
    python scripts\benchmark_parallel.py                         # the real run (see time estimate)
    python scripts\benchmark_parallel.py --n 0                   # all PDFs in data\raw\epd

The work is the real work: `airlume.pipeline.epd_parse.parse_report` (pdfplumber text
extraction plus the layout parsers) over the bulletins already downloaded to data\raw\epd.
It is CPU-bound pure Python, so threads cannot help (the GIL); processes can.

Three designs, the same function in each:

  seq    one process, one file after another. The baseline for every speed-up.
  mp     multiprocessing.Pool(w), imap_unordered, chunksize --chunk, for several w.
  async  asyncio: downloads run concurrently (a thread pool of --concurrency blocking
         requests, awaited from asyncio) and each file goes to a ProcessPoolExecutor(w)
         as soon as it lands. Download and extraction overlap.

What is measured and what is not, stated plainly:

* Wall-clock time of the whole design, including pool start-up (spawn context on every
  platform, because that is what Windows uses). Files are read once before timing so the
  disk cache does not favour later runs. Repeats are interleaved in random order so
  thermal drift is spread across designs. Reported: median of repeats, min and max.
* Speed-up S = T_seq / T_p (against the sequential run, not against 1 worker),
  efficiency E = S / p, and the Karp-Flatt experimentally determined serial fraction
  e = (1/S - 1/p) / (1 - 1/p), which stays flat when the limit is a fixed serial cost and
  grows when it is overhead or contention.
* Correctness: every design must return, for every file, the same style, row count and a
  hash of the parsed rows as the sequential run. A speed-up with different answers is not
  a speed-up; mismatches are counted and printed.
* The async design downloads from a LOCAL server that serves data\raw\epd after a fixed
  delay (--net-latency-ms). That is a model of network latency, labelled as such in the
  output; it shows how well download and CPU overlap, not how fast the Punjab EPD server
  is. The real constraint is politeness: the project's back-fill waits 2 s between
  requests to the government site, so downloading N files takes at least 2 N seconds
  whatever the design. That floor is computed and reported, not measured.
* Memory: the peak resident memory of this process and its children is sampled while each
  run goes (needs psutil; skipped without it). The laptop has 8 GB, so this matters.
* Plug the laptop in. On battery Windows throttles the CPU and the result is not
  reproducible; the script records whether it was plugged in and says so.

Output: data\eval\e5_parallel_<date>.json and a table on screen.
"""
from __future__ import annotations

import argparse
import asyncio
import functools
import hashlib
import http.server
import json
import multiprocessing as mp
import os
import platform
import random
import statistics
import sys
import tempfile
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import date
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from airlume.config import ROOT  # noqa: E402
from airlume.pipeline.epd_parse import parse_report  # noqa: E402

RAW = ROOT / "data" / "raw" / "epd"
OUT = ROOT / "data" / "eval"
POLITE_DELAY_S = 2.0  # airlume/pipeline/backfill_epd.py DELAY_S


# ---------------------------------------------------------------- the unit of work
def parse_one(path_str: str) -> tuple[str, str, int, str, str | None]:
    """Parse one bulletin. Returns (file, style, n_rows, row hash, error type or None)."""
    p = Path(path_str)
    try:
        style, rows, avg, avg_date = parse_report(p)
        sig = hashlib.sha1(repr((style, [sorted(r.__dict__.items()) for r in rows], avg,
                                 str(avg_date))).encode()).hexdigest()
        return p.name, style, len(rows), sig, None
    except Exception as e:  # a bulletin the parser cannot read is a result, identical in every design
        return p.name, "error", 0, "", type(e).__name__


# ---------------------------------------------------------------- the three designs
def run_seq(files: list[Path], **_) -> list[tuple]:
    return [parse_one(str(f)) for f in files]


def run_mp(files: list[Path], workers: int, chunk: int, **_) -> list[tuple]:
    with mp.get_context("spawn").Pool(workers) as pool:
        return list(pool.imap_unordered(parse_one, [str(f) for f in files], chunksize=chunk))


class _SlowHandler(http.server.SimpleHTTPRequestHandler):
    latency_s = 0.1

    def do_GET(self):  # noqa: N802
        time.sleep(self.latency_s)
        super().do_GET()

    def log_message(self, *a):  # silence
        pass


def _fetch(url: str) -> bytes:
    import requests
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content


async def _async_pipeline(names: list[str], workers: int, concurrency: int, port: int, tmp: Path):
    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(concurrency)
    with ThreadPoolExecutor(concurrency) as dl, \
            ProcessPoolExecutor(workers, mp_context=mp.get_context("spawn")) as pp:
        async def one(name: str):
            async with sem:
                data = await loop.run_in_executor(dl, _fetch, f"http://127.0.0.1:{port}/{quote(name)}")
            path = tmp / name
            path.write_bytes(data)
            return await loop.run_in_executor(pp, parse_one, str(path))
        return await asyncio.gather(*(one(n) for n in names))


def run_async(files: list[Path], workers: int, concurrency: int, port: int, **_) -> list[tuple]:
    with tempfile.TemporaryDirectory(prefix="e5_dl_") as t:
        return asyncio.run(_async_pipeline([f.name for f in files], workers, concurrency, port, Path(t)))


# ---------------------------------------------------------------- measurement plumbing
class RssSampler:
    """Peak resident memory of this process plus its children, sampled every 0.2 s."""

    def __init__(self) -> None:
        try:
            import psutil
            self.ps = psutil
            self.me = psutil.Process()
        except ImportError:
            self.ps = None
        self.peak = 0
        self._stop = threading.Event()
        self._t: threading.Thread | None = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                total = self.me.memory_info().rss
                for c in self.me.children(recursive=True):
                    try:
                        total += c.memory_info().rss
                    except self.ps.Error:
                        pass
                self.peak = max(self.peak, total)
            except self.ps.Error:
                pass
            self._stop.wait(0.2)

    def __enter__(self):
        if self.ps:
            self._t = threading.Thread(target=self._loop, daemon=True)
            self._t.start()
        return self

    def __exit__(self, *a):
        self._stop.set()
        if self._t:
            self._t.join()

    @property
    def peak_mb(self) -> float | None:
        return round(self.peak / 1e6, 1) if self.ps else None


def machine() -> dict:
    info = {"python": platform.python_version(), "platform": platform.platform(),
            "cpu_logical": os.cpu_count(), "plugged_in": None, "cpu_physical": None}
    try:
        import psutil
        info["cpu_physical"] = psutil.cpu_count(logical=False)
        b = psutil.sensors_battery()
        info["plugged_in"] = None if b is None else bool(b.power_plugged)
        info["ram_gb"] = round(psutil.virtual_memory().total / 1e9, 1)
    except ImportError:
        pass
    return info


def summarise(times: list[float], t_seq: float | None, p: int) -> dict:
    med = statistics.median(times)
    d = {"median_s": round(med, 2), "min_s": round(min(times), 2), "max_s": round(max(times), 2),
         "repeats": len(times)}
    if t_seq:
        s = t_seq / med
        d["speedup"] = round(s, 2)
        d["efficiency"] = round(s / p, 2)
        if p > 1:
            d["karp_flatt_serial_fraction"] = round((1 / s - 1 / p) / (1 - 1 / p), 3)
    return d


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300, help="PDFs to use (0 = all)")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--workers", default="1,2,4,8,12", help="worker counts for mp")
    ap.add_argument("--async-workers", default="4,8", help="worker counts for async")
    ap.add_argument("--chunk", type=int, default=4, help="mp chunksize")
    ap.add_argument("--concurrency", type=int, default=8, help="concurrent downloads (async)")
    ap.add_argument("--net-latency-ms", type=float, default=100.0,
                    help="simulated per-request latency of the local server (async)")
    ap.add_argument("--raw-dir", default=str(RAW))
    ap.add_argument("--seed", type=int, default=1101)
    ap.add_argument("--no-write", action="store_true", help="print only (self-test)")
    a = ap.parse_args(argv)

    raw = Path(a.raw_dir)
    files = sorted(raw.glob("*.pdf"))
    if not files:
        sys.exit(f"no PDFs in {raw}")
    rng = random.Random(a.seed)
    if a.n and a.n < len(files):
        files = sorted(rng.sample(files, a.n))
    mb = sum(f.stat().st_size for f in files) / 1e6
    m = machine()
    print(f"{len(files)} PDFs, {mb:.0f} MB, {m['cpu_logical']} logical CPUs, "
          f"{m.get('ram_gb', '?')} GB RAM, plugged in: {m['plugged_in']}")
    if m["plugged_in"] is False:
        print("WARNING: on battery. Windows throttles the CPU; plug in and run again for a result.")

    for f in files:  # warm the disk cache
        f.read_bytes()
    t0 = time.perf_counter()
    for f in files[:5]:
        parse_one(str(f))
    per_file = (time.perf_counter() - t0) / min(5, len(files))
    print(f"calibration: {per_file:.2f} s per file sequentially -> one sequential pass about "
          f"{per_file * len(files) / 60:.1f} min")

    mp_w = [int(x) for x in a.workers.split(",") if x]
    as_w = [int(x) for x in a.async_workers.split(",") if x]
    configs = [("seq", 1)] + [("mp", w) for w in mp_w] + [("async", w) for w in as_w]

    server = None
    port = 0
    if as_w:
        _SlowHandler.latency_s = a.net_latency_ms / 1000
        server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(_SlowHandler, directory=str(raw)))
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()

    runners = {"seq": run_seq, "mp": run_mp, "async": run_async}
    results: dict[tuple, list[float]] = {c: [] for c in configs}
    rss: dict[tuple, float | None] = {}
    baseline: dict[str, tuple] = {}
    mismatches: dict[tuple, int] = {c: 0 for c in configs}
    errors_in_parser = 0

    for rep in range(a.repeats):
        order = configs[:]
        random.Random(a.seed + rep).shuffle(order)
        for design, w in order:
            with RssSampler() as s:
                t = time.perf_counter()
                out = runners[design](files, workers=w, chunk=a.chunk,
                                      concurrency=a.concurrency, port=port)
                dt = time.perf_counter() - t
            results[(design, w)].append(dt)
            if s.peak_mb is not None:
                rss[(design, w)] = max(rss.get((design, w)) or 0, s.peak_mb)
            got = {r[0]: r[1:4] for r in out}
            if design == "seq" and not baseline:
                baseline = got
                errors_in_parser = sum(1 for r in out if r[4])
            elif baseline:
                mismatches[(design, w)] += sum(1 for k, v in got.items() if baseline.get(k) != v) \
                    + abs(len(got) - len(baseline))
            print(f"  repeat {rep + 1}/{a.repeats}  {design:<5} w={w:<2}  {dt:7.1f} s")
    if server:
        server.shutdown()

    t_seq = statistics.median(results[("seq", 1)]) if results[("seq", 1)] else None
    rows = []
    for (design, w), ts in results.items():
        d = {"design": design, "workers": w, **summarise(ts, t_seq, w),
             "peak_rss_mb": rss.get((design, w)), "result_mismatches_vs_seq": mismatches[(design, w)]}
        rows.append(d)

    print(f"\n{'design':<6}{'w':>3}{'median s':>10}{'speedup':>9}{'effic.':>8}{'KarpFl.':>9}"
          f"{'peak MB':>9}{'mismatch':>9}")
    for d in rows:
        print(f"{d['design']:<6}{d['workers']:>3}{d['median_s']:>10}{d.get('speedup', ''):>9}"
              f"{d.get('efficiency', ''):>8}{d.get('karp_flatt_serial_fraction', ''):>9}"
              f"{d['peak_rss_mb'] if d['peak_rss_mb'] is not None else '':>9}"
              f"{d['result_mismatches_vs_seq']:>9}")
    bad = sum(d["result_mismatches_vs_seq"] for d in rows)
    print("\nresults identical to sequential in every design" if bad == 0
          else f"\nWARNING: {bad} result mismatches against the sequential run")

    report = {
        "date": date.today().isoformat(), "machine": m, "files": len(files), "pdf_mb": round(mb, 1),
        "seed": a.seed, "repeats": a.repeats, "mp_chunksize": a.chunk,
        "async": {"concurrency": a.concurrency, "simulated_net_latency_ms": a.net_latency_ms,
                  "note": "downloads come from a local server with a fixed delay: a model of latency, "
                          "not a measurement of the EPD server"},
        "politeness_floor_s_for_these_files": len(files) * POLITE_DELAY_S,
        "politeness_floor_s_for_all_1990": 1990 * POLITE_DELAY_S,
        "politeness_note": "the real back-fill waits 2 s between requests, so downloading cannot take "
                           "less than 2 s per file whatever the design; computed, not measured",
        "parser_errors_in_baseline": errors_in_parser,
        "sequential_s_per_file": round((t_seq or 0) / len(files), 3),
        "rows": rows,
    }
    if a.no_write:
        print("(self-test: nothing written)")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"e5_parallel_{report['date']}.json"
    p.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"written {p}")
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main(sys.argv[1:]))
