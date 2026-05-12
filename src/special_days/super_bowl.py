"""NFL Super Bowl date lookup.

    >>> from special_days import super_bowl
    >>> super_bowl.date(2025)
    datetime.date(2025, 2, 9)
    >>> super_bowl.is_super_bowl_sunday(date(2025, 2, 9))
    True

The shipped snapshot answers offline. When a requested year is unknown,
the lookup transparently refreshes from Wikidata (unless
``allow_network=False``) and updates a per-user cache.
"""

from __future__ import annotations

import datetime
import json
from collections.abc import Iterable
from importlib import resources
from pathlib import Path

from . import _cache, _wikidata
from ._event import _Event

_CACHE_FILENAME = "super_bowl.json"
_SNAPSHOT_RESOURCE = ("special_days.data", "super_bowl.json")


def _load_snapshot() -> dict[int, datetime.date]:
    """Load the {year: date} mapping shipped inside the package."""
    package, name = _SNAPSHOT_RESOURCE
    text = resources.files(package).joinpath(name).read_text("utf-8")
    raw = json.loads(text)
    return {int(y): datetime.date.fromisoformat(v) for y, v in raw.items()}


def _cache_path() -> Path:
    return _cache.default_cache_dir() / _CACHE_FILENAME


def _fetch_from_wikidata() -> dict[int, datetime.date]:
    """Refresh from Wikidata and persist to the user cache."""
    fresh = _wikidata.fetch_super_bowl_dates()
    if fresh:
        _cache.write_cache(_cache_path(), fresh)
    return fresh


def all_known() -> dict[int, datetime.date]:
    """Return everything we know offline (cache merged over snapshot)."""
    merged = dict(_load_snapshot())
    merged.update(_cache.read_cache(_cache_path()))
    return merged


def date(year: int, allow_network: bool = True) -> datetime.date:
    """Return the date of the Super Bowl played in the given year.

    Looks in local data first (cache, then shipped snapshot). If the
    year isn't known and ``allow_network`` is True, refreshes from
    Wikidata. Raises ``KeyError`` if the year still can't be resolved.
    """
    known = all_known()
    if year in known:
        return known[year]
    if not allow_network:
        raise KeyError(year)
    fresh = _fetch_from_wikidata()
    if year in fresh:
        return fresh[year]
    raise KeyError(year)


def is_super_bowl_sunday(d: datetime.date, allow_network: bool = False) -> bool:
    """Return True iff ``d`` is the date of a Super Bowl.

    Defaults to local-only lookup: checking past dates shouldn't ever
    hit the network, and a "no" for a year we've never heard of is the
    right answer for the vast majority of callers.
    """
    try:
        return date(d.year, allow_network=allow_network) == d
    except KeyError:
        return False


def refresh() -> dict[int, datetime.date]:
    """Force a refresh from Wikidata. Raises WikidataUnavailable on failure."""
    return _fetch_from_wikidata()


# ---------------------------------------------------------------------------
# holidays-compatible class API
# ---------------------------------------------------------------------------

# Super Bowl I was played in 1967. The edition number for a given year
# is `year - 1966`. Super Bowl 50 (2016) was officially marketed with
# the Arabic numeral; every other edition uses Roman.
_SB_OFFSET = 1966


def _edition_label(year: int) -> str:
    n = year - _SB_OFFSET
    if n == 50:
        return "Super Bowl 50"
    return f"Super Bowl {_roman(n)}"


def _roman(n: int) -> str:
    table = [
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    out: list[str] = []
    for value, sym in table:
        while n >= value:
            out.append(sym)
            n -= value
    return "".join(out)


class SuperBowl(_Event):
    """Lazy date-keyed lookup of NFL Super Bowl dates.

        >>> from datetime import date
        >>> from special_days import SuperBowl
        >>> sb = SuperBowl()
        >>> date(2025, 2, 9) in sb
        True
        >>> sb[date(2025, 2, 9)]
        'Super Bowl'

    Use ``label_with_edition=True`` to get edition-numbered labels
    (``"Super Bowl LIX"``) instead of the constant ``"Super Bowl"``.
    The constant form makes it easy to look up per-event metadata
    (icons, calendar colors, ...) in a flat dict keyed by name.

    Note: with ``years=[...]`` containing years not in the shipped
    snapshot or the local cache, construction will hit the network and
    can raise ``_wikidata.WikidataUnavailable`` if Wikidata is down.
    Wrap eager preloads in a try/except if that matters to your caller.
    """

    name = "Super Bowl"

    def __init__(
        self,
        years: int | Iterable[int] | None = None,
        allow_network: bool = True,
        label_with_edition: bool = False,
    ) -> None:
        self._label_with_edition: bool = label_with_edition
        super().__init__(years=years, allow_network=allow_network)

    def _date_lookup(self, year: int) -> datetime.date:
        return date(year, allow_network=self._allow_network)

    def _label_for(self, year: int) -> str:
        if self._label_with_edition:
            return _edition_label(year)
        return self.name

    def _upstream_refresh(self) -> None:
        refresh()
