"""Academy Awards ("Oscars") ceremony date lookup.

    >>> from special_days import oscars
    >>> oscars.date(2025)
    datetime.date(2025, 3, 2)
    >>> oscars.is_oscars_night(date(2025, 3, 2))
    True

Same offline-first behavior as the Super Bowl module: a snapshot ships
with the package, the lookup transparently refreshes from Wikidata for
unknown years, and a per-user cache holds the freshest data.
"""

from __future__ import annotations

import datetime
import json
from collections.abc import Iterable
from importlib import resources
from pathlib import Path

from . import _cache, _wikidata
from ._event import _Event

_CACHE_FILENAME = "oscars.json"
_SNAPSHOT_RESOURCE = ("special_days.data", "oscars.json")


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
    fresh = _wikidata.fetch_oscars_dates()
    if fresh:
        _cache.write_cache(_cache_path(), fresh)
    return fresh


def all_known() -> dict[int, datetime.date]:
    """Return everything we know offline (cache merged over snapshot)."""
    merged = dict(_load_snapshot())
    merged.update(_cache.read_cache(_cache_path()))
    return merged


def date(year: int, allow_network: bool = True) -> datetime.date:
    """Return the date of the Academy Awards ceremony in the given year.

    Note: the Oscars ceremony year is the year it was held, which is
    usually the year after the films it honors. So ``date(2025)``
    returns the ceremony date for the 97th Academy Awards (March 2,
    2025), which awarded films released in 2024.
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


def is_oscars_night(d: datetime.date, allow_network: bool = False) -> bool:
    """Return True iff ``d`` is the date of an Academy Awards ceremony.

    Local-only by default, mirroring ``super_bowl.is_super_bowl_sunday``.
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

# 1st Academy Awards was held in 1929; edition number for ceremony in
# year Y is Y - 1928.
_OSCARS_OFFSET = 1928


def _edition_label(year: int) -> str:
    return f"{_ordinal(year - _OSCARS_OFFSET)} Academy Awards"


def _ordinal(n: int) -> str:
    """English ordinal suffix: 1 -> '1st', 22 -> '22nd', 113 -> '113th'."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class Oscars(_Event):
    """Lazy date-keyed lookup of Academy Awards ceremony dates.

        >>> from datetime import date
        >>> from special_days import Oscars
        >>> oscars = Oscars()
        >>> date(2025, 3, 2) in oscars
        True
        >>> oscars[date(2025, 3, 2)]
        'Academy Awards'

    Use ``label_with_edition=True`` to get edition-numbered labels
    (``"97th Academy Awards"``) instead of the constant
    ``"Academy Awards"``. The constant form makes name-keyed lookups
    (icons, calendar colors, ...) trivial.

    Note: with ``years=[...]`` containing years not in the shipped
    snapshot or the local cache, construction will hit the network and
    can raise ``_wikidata.WikidataUnavailable`` if Wikidata is down.
    """

    name = "Academy Awards"

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
