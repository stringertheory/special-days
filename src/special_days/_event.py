"""Abstract base for date-keyed event lookups.

Subclasses give us:
  - a ``name`` attribute (the constant label, e.g. "Super Bowl")
  - ``_date_lookup(year)`` that returns the date for that year or
    raises ``KeyError`` if not known.

In return they get a ``dict``-like object compatible with the
``holidays`` package: ``date in sb``, ``sb[date]``, ``sb.get(date)``,
``sb.get_list(date)``, iteration over loaded keys, and lazy per-year
population on first access.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date


class _Event(dict):
    """Lazy date-keyed dict of one calendar-disrupting event series."""

    name: str = ""  # subclasses override

    def __init__(
        self,
        years: int | Iterable[int] | None = None,
        allow_network: bool = True,
    ) -> None:
        super().__init__()
        self._allow_network: bool = allow_network
        self._loaded_years: set[int] = set()
        if years is not None:
            if isinstance(years, int):
                years = [years]
            for year in years:
                self._ensure_year(year)

    # --- holidays-compatible dict surface --------------------------------

    def __contains__(self, key: object) -> bool:
        if isinstance(key, date):
            self._ensure_year(key.year)
        return super().__contains__(key)

    def __getitem__(self, key: date) -> str:
        if isinstance(key, date):
            self._ensure_year(key.year)
        return super().__getitem__(key)

    def get(self, key: date, default: str | None = None) -> str | None:
        if isinstance(key, date):
            self._ensure_year(key.year)
        return super().get(key, default)

    def get_list(self, key: date) -> list[str]:
        """Return all labels for ``key`` as a list. One per date for now.

        Mirrors ``holidays.HolidayBase.get_list``. A single event can
        only contribute one label per date, but the merged
        :class:`LazyDateMap` view uses this to gather labels from
        multiple sources.
        """
        if isinstance(key, date):
            self._ensure_year(key.year)
        if super().__contains__(key):
            return [super().__getitem__(key)]
        return []

    # --- lazy machinery --------------------------------------------------

    def _ensure_year(self, year: int) -> None:
        """Populate self with this year's date(s), if not already done."""
        if year in self._loaded_years:
            return
        try:
            event_date = self._date_lookup(year)
        except KeyError:
            self._loaded_years.add(year)
            return
        dict.__setitem__(self, event_date, self._label_for(year))
        self._loaded_years.add(year)

    def refresh(self) -> None:
        """Force-refresh from upstream and forget locally-loaded years.

        Raises :class:`RuntimeError` if the instance was constructed
        with ``allow_network=False``. ``refresh()`` exists specifically
        to fetch fresh data, so silently no-op'ing it would hide bugs;
        the caller should either drop the flag or not call this.
        """
        if not self._allow_network:
            raise RuntimeError(
                f"{type(self).__name__}.refresh() requires network "
                "access, but this instance was constructed with "
                "allow_network=False."
            )
        self._upstream_refresh()
        dict.clear(self)
        self._loaded_years.clear()

    # --- subclass hooks --------------------------------------------------

    def _date_lookup(self, year: int) -> date:
        raise NotImplementedError

    def _upstream_refresh(self) -> None:
        raise NotImplementedError

    def _label_for(self, year: int) -> str:
        return self.name
