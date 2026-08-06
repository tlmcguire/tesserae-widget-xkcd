"""xkcd_comic, xkcd.com's undocumented-but-ancient JSON endpoint.

xkcd doesn't publish an API spec, but https://xkcd.com/info.0.json
(latest) and https://xkcd.com/<n>/info.0.json (specific) have shipped
the same shape for 15+ years and are what nearly every third-party
xkcd client reads from, including the official Android/iOS apps'
predecessors. That track record is why this widget is catalogued as
Best-effort rather than Stable (see docs/widgets/tiers.md): it should
keep working, but there's no changelog to watch if it doesn't.

The ``alt`` field in that JSON is the comic's hovertext, the joke
xkcd.com normally reveals only on mouse-over. There's no cursor on an
e-ink panel, so this widget just prints it as a caption instead.

Comic #404 is xkcd's own joke (the page literally 404s); it's skipped
when picking a random comic and reported with a friendly message if
requested directly.
"""

from __future__ import annotations

import contextlib
import json
import random
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

LATEST_URL = "https://xkcd.com/info.0.json"
NUMBERED_URL = "https://xkcd.com/{num}/info.0.json"
LATEST_CACHE_TTL_S = 30 * 60  # comics post ~3x/week; no need to poll harder
HTTP_TIMEOUT_S = 15
USER_AGENT = "tesserae/0.1 (+xkcd_comic)"
JOKE_404_COMIC = 404
DEFAULT_RANDOM_REFRESH_HOURS = 24


def _get_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))  # type: ignore[no-any-return]


def _shape(entry: dict[str, Any]) -> dict[str, Any]:
    date = ""
    with contextlib.suppress(KeyError, ValueError):
        date = f"{int(entry['year']):04d}-{int(entry['month']):02d}-{int(entry['day']):02d}"
    num = entry.get("num")
    return {
        "num": num,
        "title": entry.get("safe_title") or entry.get("title") or "",
        "img": entry.get("img") or "",
        "alt": entry.get("alt") or "",
        "date": date,
        "link_page": f"https://xkcd.com/{num}/" if num else "https://xkcd.com/",
    }


def _friendly_error(err: Exception, *, comic_number: int | None = None) -> str:
    if isinstance(err, urllib.error.HTTPError):
        if err.code == 404:
            if comic_number == JOKE_404_COMIC:
                return "xkcd #404 is the joke, the page doesn't exist. Pick another number."
            return f"No xkcd comic #{comic_number}." if comic_number else "Comic not found."
        return f"xkcd.com returned HTTP {err.code}. Try again shortly."
    if isinstance(err, urllib.error.URLError):
        return "Couldn't reach xkcd.com right now."
    if isinstance(err, (json.JSONDecodeError, ValueError)):
        return "xkcd.com sent back something this widget couldn't parse."
    return f"Couldn't load the comic ({type(err).__name__})."


def _cache_path(data_dir: Path, key: str) -> Path:
    return data_dir / f"xkcd_{key}.json"


def _read_cache(path: Path, *, max_age_s: float | None) -> dict[str, Any] | None:
    if not path.exists():
        return None
    if max_age_s is not None and time.time() - path.stat().st_mtime > max_age_s:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(path: Path, payload: dict[str, Any]) -> None:
    with contextlib.suppress(OSError):
        path.write_text(json.dumps(payload), encoding="utf-8")


def _fetch_latest(data_dir: Path) -> dict[str, Any]:
    cache = _cache_path(data_dir, "latest")
    cached = _read_cache(cache, max_age_s=LATEST_CACHE_TTL_S)
    if cached is not None:
        return cached
    entry = _get_json(LATEST_URL)
    shaped = _shape(entry)
    _write_cache(cache, shaped)
    return shaped


def _fetch_numbered(data_dir: Path, num: int) -> dict[str, Any]:
    # Past comics never change, so this cache never expires.
    cache = _cache_path(data_dir, f"n{num}")
    cached = _read_cache(cache, max_age_s=None)
    if cached is not None:
        return cached
    entry = _get_json(NUMBERED_URL.format(num=num))
    shaped = _shape(entry)
    _write_cache(cache, shaped)
    return shaped


def _fetch_random(data_dir: Path, *, refresh_hours: float) -> dict[str, Any]:
    state_path = data_dir / "xkcd_random_state.json"
    refresh_s = max(0.0, refresh_hours) * 3600
    state = _read_cache(state_path, max_age_s=refresh_s if refresh_s > 0 else None)
    if state is not None and state.get("num"):
        cached = _read_cache(_cache_path(data_dir, f"n{state['num']}"), max_age_s=None)
        if cached is not None:
            return cached

    latest = _fetch_latest(data_dir)
    latest_num = int(latest["num"] or 1)
    pick = random.randint(1, max(1, latest_num))
    if pick == JOKE_404_COMIC:
        # One deterministic dodge is simpler than a retry loop. Step down
        # (or up, from 1) rather than jumping to latest_num, which would
        # itself be 404 in the pathological case where that's the newest
        # comic number seen.
        pick = pick - 1 if pick > 1 else pick + 1

    shaped = _fetch_numbered(data_dir, pick)
    _write_cache(state_path, {"num": pick})
    return shaped


def fetch(
    options: dict[str, Any], settings: dict[str, Any], *, ctx: dict[str, Any]
) -> dict[str, Any]:
    del settings
    mode = (options.get("mode") or "latest").strip().lower()
    data_dir = Path(ctx["data_dir"])
    data_dir.mkdir(parents=True, exist_ok=True)

    comic_number: int | None = None
    try:
        if mode == "fixed":
            comic_number = int(options.get("comic_number") or 353)
            if comic_number == JOKE_404_COMIC:
                return {
                    "error": "xkcd #404 is the joke, the page doesn't exist. Pick another number."
                }
            if comic_number < 1:
                return {"error": "Comic numbers start at 1."}
            shaped = _fetch_numbered(data_dir, comic_number)
        elif mode == "random":
            hours = options.get("random_refresh_hours")
            hours = float(hours) if hours not in (None, "") else DEFAULT_RANDOM_REFRESH_HOURS
            shaped = _fetch_random(data_dir, refresh_hours=hours)
        else:
            shaped = _fetch_latest(data_dir)
    except Exception as err:  # noqa: BLE001 - translated to a friendly cell message below
        return {"error": _friendly_error(err, comic_number=comic_number)}

    shaped["mode"] = mode
    return shaped
