"""Read-only union view over date-keyed dict-likes.

Used to compose this package's eager :class:`~special_days.EventDict`
instances with third-party lazy sources like ``holidays.HolidayBase``.
None of the sources are materialized: ``in``/``[]``/``.get``/
``.get_list`` queries are forwarded to each source in turn, so any
per-year laziness on the source side is preserved.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import date

from .event import normalize_date


class LazyDateMap:
    """Read-only union view; lookups walk sources in order."""

    def __init__(self, *sources: Mapping[date, str]) -> None:
        self.sources: tuple[Mapping[date, str], ...] = sources

    def __contains__(self, key: object) -> bool:
        norm = normalize_date(key)
        return any(norm in s for s in self.sources)

    def __getitem__(self, key: date) -> str:
        norm = normalize_date(key)
        for s in self.sources:
            if norm in s:
                return s[norm]  # type: ignore[index]
        raise KeyError(key)

    def get(self, key: date, default: str | None = None) -> str | None:
        norm = normalize_date(key)
        for s in self.sources:
            if norm in s:
                return s[norm]  # type: ignore[index]
        return default

    def get_list(self, key: date) -> list[str]:
        """All labels for ``key`` across every source. Delegates to
        each source's ``get_list`` if it has one (so ``holidays``'s
        semicolon-joined values get split correctly), otherwise falls
        back to the source's value.
        """
        norm = normalize_date(key)
        out: list[str] = []
        for s in self.sources:
            if hasattr(s, "get_list"):
                out.extend(s.get_list(norm))
            elif norm in s:
                out.append(s[norm])  # type: ignore[index]
        return out

    def __iter__(self) -> Iterator[date]:
        seen: set[date] = set()
        for s in self.sources:
            for k in s:
                if k not in seen:
                    seen.add(k)
                    yield k

    def __len__(self) -> int:
        return sum(1 for _ in self)


def union(*sources: Mapping[date, str]) -> LazyDateMap:
    """Read-only union of date-keyed dict-likes.

    >>> from datetime import date
    >>> from special_days import SuperBowl, union
    >>> us_like = {date(2025, 7, 4): "Independence Day"}
    >>> days = union(us_like, SuperBowl())
    >>> date(2025, 7, 4) in days
    True
    >>> date(2025, 2, 9) in days
    True
    >>> days.get_list(date(2025, 2, 9))
    ['Super Bowl']
    """
    return LazyDateMap(*sources)
