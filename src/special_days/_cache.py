"""On-disk cache for {year: date} mappings.

The cache file is plain JSON: ``{"2025": "2025-02-09", ...}``. We treat
any read failure (missing file, bad JSON, wrong shape) as a cache miss
and return ``{}`` — the caller decides what to do next.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path


def read_cache(path: str | os.PathLike[str]) -> dict[int, date]:
    """Return {year: date} from a cache file, or {} if unreadable."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[int, date] = {}
    for key, value in data.items():
        try:
            year = int(key)
            d = date.fromisoformat(value)
        except (TypeError, ValueError):
            continue
        out[year] = d
    return out


def write_cache(path: str | os.PathLike[str], data: dict[int, date]) -> None:
    """Write {year: date} to a cache file, creating parent dirs.

    Best-effort: any OSError (no permission, read-only filesystem,
    no space, ...) is swallowed. The cache is an optimization, not a
    correctness requirement -- the caller has already computed the
    data and is about to return it; an unwritable cache should cost
    a re-fetch next time, not crash the lookup. Mirrors the
    permissive behavior of read_cache.
    """
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {str(year): d.isoformat() for year, d in data.items()}
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except OSError:
        pass


def default_cache_dir() -> Path:
    """Return the per-user cache directory for this package."""
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "special-days"
