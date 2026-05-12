"""Read-only union view over date-keyed dict-likes.

Used to compose multiple event objects (and/or third-party objects like
``holidays.HolidayBase`` instances) into a single lazy lookup. None of
the sources are materialized: ``in``/``[]``/``.get``/``.get_list``
queries are forwarded to each source in turn, so per-year laziness on
either side is preserved.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import date


class LazyDateMap:
    """Lazy union view. Read-only; lookups walk sources in order."""

    def __init__(self, *sources: Mapping[date, str]) -> None:
        self._sources: tuple[Mapping[date, str], ...] = sources

    def __contains__(self, key: object) -> bool:
        return any(key in s for s in self._sources)

    def __getitem__(self, key: date) -> str:
        for s in self._sources:
            if key in s:
                return s[key]
        raise KeyError(key)

    def get(self, key: date, default: str | None = None) -> str | None:
        for s in self._sources:
            if key in s:
                return s[key]
        return default

    def get_list(self, key: date) -> list[str]:
        """All labels for ``key`` from every source. Mirrors
        ``holidays.HolidayBase.get_list``; delegates to each source's
        ``get_list`` if it has one (so ``holidays``'s semicolon-joined
        values get split correctly), otherwise falls back to its value.
        """
        out: list[str] = []
        for s in self._sources:
            if hasattr(s, "get_list"):
                out.extend(s.get_list(key))
            elif key in s:
                out.append(s[key])
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

    def refresh(self) -> None:
        """Refresh every source that supports it.

        Sources without a ``refresh`` method are silently skipped (e.g.
        plain dicts, ``holidays.HolidayBase`` instances). Errors from any
        source — including ``_Event.refresh()``'s ``RuntimeError`` under
        ``allow_network=False`` — propagate; later sources are not
        refreshed in that case. If you want partial-failure behavior,
        loop over the underlying sources yourself.
        """
        for s in self._sources:
            refresh = getattr(s, "refresh", None)
            if callable(refresh):
                refresh()


def union(*sources: Mapping[date, str]) -> LazyDateMap:
    """Lazy read-only union of date-keyed dict-likes.

    >>> import holidays
    >>> from special_days import SuperBowl, union
    >>> days = union(holidays.US(), SuperBowl())
    >>> from datetime import date
    >>> date(2025, 2, 9) in days     # doctest: +SKIP
    True
    """
    return LazyDateMap(*sources)
