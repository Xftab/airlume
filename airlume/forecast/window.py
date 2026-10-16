"""Lowest-AQI window in the relayed 24-hour forecast (plan 4.6).

Finds the contiguous window of `hours` consecutive forecast hours with the lowest
mean predicted AQI, from the most recent forecast issue of one source.

Two deliberate limits, both stated wherever the result is shown:

* **It is a prediction, never advice.** The plan is explicit that this is never
  phrased as guidance about going out, exercising or health. The text here says
  what is predicted and how wrong that source usually is; it never suggests the
  reader do anything.
* **It is city-level, not per-station.** The plan's wording ("for the nearest
  station") assumed a per-station forecast. The portal publishes its 24-hour
  forecast for Lahore as a whole, and CAMS resolves to roughly one 45 km cell over
  the city, so no per-station forecast exists to use. Saying "near Gulberg III"
  would imply a spatial precision neither source has.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Window:
    start: pd.Timestamp
    end: pd.Timestamp          # inclusive: the last forecast hour in the window
    mean_aqi: float
    source: str
    issued_at: pd.Timestamp
    n_hours: int

    @property
    def hours_span(self) -> int:
        return int((self.end - self.start).total_seconds() // 3600) + 1


def lowest_window(forecasts: pd.DataFrame, hours: int = 2,
                  source: str | None = None,
                  now: pd.Timestamp | None = None) -> Window | None:
    """Lowest-mean contiguous window in the latest issue of a forecast source.

    `forecasts`: city_id, issued_at, target_ts, aqi, source.

    Only hours that are actually consecutive are considered: a gap in the series
    would otherwise let a "window" span a missing hour and report a mean over
    times that were never adjacent.

    Hours already past are dropped. The portal's forecast is issued hourly and
    still contains the hour it was issued in, so without this the "lowest window
    in the next 24 hours" could point at a time that has already gone by --- which
    it did on the first live run.

    Returns None when what remains has no run of `hours` consecutive hours.
    """
    if forecasts.empty or hours < 1:
        return None
    df = forecasts.copy()
    df["target_ts"] = pd.to_datetime(df["target_ts"], utc=True)
    df["issued_at"] = pd.to_datetime(df["issued_at"], utc=True)
    df["aqi"] = pd.to_numeric(df["aqi"], errors="coerce")
    if source is not None:
        df = df[df["source"] == source]
    df = df.dropna(subset=["aqi"])
    if df.empty:
        return None

    # The most recent issue of whichever source we are using.
    src = source or df.sort_values("issued_at")["source"].iloc[-1]
    df = df[df["source"] == src]
    latest_issue = df["issued_at"].max()
    df = df[df["issued_at"] == latest_issue].sort_values("target_ts")
    df = df.drop_duplicates(subset=["target_ts"], keep="last")

    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now).tz_convert("UTC")
    df = df[df["target_ts"] >= now.floor("h")]
    if len(df) < hours:
        return None

    best: Window | None = None
    ts = df["target_ts"].tolist()
    aqi = df["aqi"].tolist()
    for i in range(len(df) - hours + 1):
        span = ts[i:i + hours]
        # consecutive hours only
        if any((span[j + 1] - span[j]) != pd.Timedelta(hours=1) for j in range(len(span) - 1)):
            continue
        mean = sum(aqi[i:i + hours]) / hours
        if best is None or mean < best.mean_aqi:
            best = Window(start=span[0], end=span[-1], mean_aqi=float(mean),
                          source=src, issued_at=latest_issue, n_hours=hours)
    return best


@dataclass(frozen=True)
class Outlook:
    """The hours still ahead in one source's most recent forecast issue."""
    source: str
    issued_at: pd.Timestamp
    n_hours: int
    mean_aqi: float
    max_aqi: float
    max_at: pd.Timestamp
    min_aqi: float
    min_at: pd.Timestamp


def outlook(forecasts: pd.DataFrame, source: str,
            now: pd.Timestamp | None = None) -> Outlook | None:
    """Summarise the future hours of one source's latest issue.

    Per source, deliberately: the two relayed forecasts are issued at different
    times, and taking the latest issue across sources together silently drops
    whichever was issued earlier.
    """
    if forecasts.empty:
        return None
    df = forecasts[forecasts["source"] == source].copy()
    if df.empty:
        return None
    df["target_ts"] = pd.to_datetime(df["target_ts"], utc=True)
    df["issued_at"] = pd.to_datetime(df["issued_at"], utc=True)
    df["aqi"] = pd.to_numeric(df["aqi"], errors="coerce")
    df = df.dropna(subset=["aqi"])
    if df.empty:
        return None
    latest = df["issued_at"].max()
    df = df[df["issued_at"] == latest].drop_duplicates(subset=["target_ts"], keep="last")
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now).tz_convert("UTC")
    df = df[df["target_ts"] >= now.floor("h")].sort_values("target_ts")
    if df.empty:
        return None
    hi = df.loc[df["aqi"].idxmax()]
    lo = df.loc[df["aqi"].idxmin()]
    return Outlook(source=source, issued_at=latest, n_hours=len(df),
                   mean_aqi=float(df["aqi"].mean()),
                   max_aqi=float(hi["aqi"]), max_at=hi["target_ts"],
                   min_aqi=float(lo["aqi"]), min_at=lo["target_ts"])


def describe(window: Window | None, mae: float | None = None,
             tz: str = "Asia/Karachi", source_label: str | None = None) -> str:
    """One sentence, written by code from the numbers. A prediction, not advice."""
    if window is None:
        return "No 24-hour forecast is stored yet, so no window can be given."
    start = window.start.tz_convert(tz)
    end = (window.end + pd.Timedelta(hours=1)).tz_convert(tz)   # end of the last hour
    label = source_label or window.source
    text = (f"Lowest predicted AQI in Lahore over the next 24 hours: "
            f"{start:%H:%M}–{end:%H:%M} on {start:%d %b} "
            f"(around {window.mean_aqi:.0f}), from the {label} forecast.")
    if mae is not None:
        text += (f" That source has been out by about {mae:.0f} AQI points on average "
                 "so far, so treat the figure as approximate.")
    else:
        text += " There is not yet enough scored history to say how accurate that source is."
    return text
