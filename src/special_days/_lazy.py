"""Read-only lazy union view over date-keyed dict-likes.

Used to compose multiple event objects (and/or third-party objects like
``holidays.HolidayBase`` instances) into a single lookup. None of the
sources are materialized: ``in``/``[]``/``.get``/``.get_list`` queries
are forwarded to each source in turn, so per-year laziness on either
side is preserved.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import date, datetime


def _normalize_date(key: object) -> object:
    if isinstance(key, datetime):
        return key.date()
    return key


class LazyDateMap:
    """Lazy union view. Read-only; lookups walk sources in order."""

    def __init__(self, *sources: Mapping[date, str]) -> None:
        self._sources: tuple[Mapping[date, str], ...] = sources

    def __contains__(self, key: object) -> bool:
        key = _normalize_date(key)
        return any(key in s for s in self._sources)

    def __getitem__(self, key: date) -> str:
        norm = _normalize_date(key)
        for s in self._sources:
            if norm in s:
                return s[norm]  # type: ignore[index]
        raise KeyError(key)

    def get(self, key: date, default: str | None = None) -> str | None:
        norm = _normalize_date(key)
        for s in self._sources:
            if norm in s:
                return s[norm]  # type: ignore[index]
        return default

    def get_list(self, key: date) -> list[str]:
        """All labels for ``key`` from every source. Mirrors
        ``holidays.HolidayBase.get_list``; delegates to each source's
        ``get_list`` if it has one (so ``holidays``'s semicolon-joined
        values get split correctly), otherwise falls back to its value.
        """
        norm = _normalize_date(key)
        out: list[str] = []
        for s in self._sources:
            if hasattr(s, "get_list"):
                out.extend(s.get_list(norm))
            elif norm in s:
                out.append(s[norm])  # type: ignore[index]
        return out

    def __iter__(self) -> Iterator[date]:
        seen: set[date] = set()
        for s in self._sources:
            for k in s:
                if k not in seen:
                    seen.add(k)
                    yield k

    def __len__(self) -> int:
        return sum(1 for _ in self)


def union(*sources: Mapping[date, str]) -> LazyDateMap:
    """Lazy read-only union of date-keyed dict-likes.

    >>> from datetime import date
    >>> from special_days import SuperBowl, union
    >>> us_like = {date(2025, 7, 4): "Independence Day"}
    >>> days = union(us_like, SuperBowl())
    >>> date(2025, 7, 4) in days
    True
    >>> date(2025, 2, 9) in days
    True
    >>> sorted(days.get_list(date(2025, 2, 9)))
    ['Super Bowl']
    """
    return LazyDateMap(*sources)
