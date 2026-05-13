"""Generic event-date lookup.

A package event series (Super Bowl, Oscars, ...) is described by an
:class:`Event` value: a constant name, a shipped JSON snapshot of all
known dates, and (optionally) a date-keyed edition labeller. Each
:class:`Event` exposes:

* a year-keyed module-level API via :meth:`Event.first_date`,
  :meth:`Event.dates`, :meth:`Event.all_known`, and
  :meth:`Event.contains_date`,
* a date-keyed class API via :meth:`Event.cls`, which returns a
  ``dict[date, str]`` subclass compatible with the
  `holidays <https://pypi.org/project/holidays/>`_ package.

The package ships with the full snapshot inside the wheel -- every
lookup is local and answers in microseconds with no network. Snapshots
are refreshed in CI from Wikidata; ``pip install --upgrade`` pulls
fresh data.
"""

from __future__ import annotations

import datetime
import json
from collections.abc import Callable, Iterable
from importlib import resources
from typing import ClassVar


def _normalize_date(key: object) -> object:
    """Coerce a ``datetime.datetime`` to its ``date`` part; pass
    everything else through unchanged. Mirrors ``holidays.HolidayBase``.
    """
    if isinstance(key, datetime.datetime):
        return key.date()
    return key


def _check_year(year: object) -> int:
    """Reject non-``int`` years before they reach the lookup table."""
    if not isinstance(year, int):
        raise TypeError(f"year must be int, got {type(year).__name__}")
    return year


class _EventDict(dict[datetime.date, str]):
    """Lazy date-keyed dict for one event series.

    Subclasses set the ``_event`` class attribute via :meth:`Event.cls`.
    Mirrors the dict-like surface of `holidays.HolidayBase
    <https://pypi.org/project/holidays/>`_: only years explicitly
    queried (or named in ``years=[...]`` at construction time) get
    loaded. ``datetime`` keys are normalized to ``date`` automatically.
    """

    _event: ClassVar[Event]  # set by Event.cls()

    def __init__(
        self,
        years: int | Iterable[int] | None = None,
        label_with_edition: bool = False,
    ) -> None:
        super().__init__()
        self._label_with_edition: bool = label_with_edition
        self._loaded_years: set[int] = set()
        if isinstance(years, int):
            years = [years]
        for year in years or ():
            self._ensure_year(_check_year(year))

    @property
    def name(self) -> str:
        return self._event.name

    def __contains__(self, key: object) -> bool:
        norm = _normalize_date(key)
        if not isinstance(norm, datetime.date):
            return False
        self._ensure_year(norm.year)
        return super().__contains__(norm)

    def __getitem__(self, key: datetime.date) -> str:
        norm = _normalize_date(key)
        if not isinstance(norm, datetime.date):
            raise KeyError(key)
        self._ensure_year(norm.year)
        return super().__getitem__(norm)

    def get(  # type: ignore[override]
        self, key: object, default: str | None = None
    ) -> str | None:
        norm = _normalize_date(key)
        if not isinstance(norm, datetime.date):
            return default
        self._ensure_year(norm.year)
        return super().get(norm, default)

    def get_list(self, key: object) -> list[str]:
        """All labels at ``key`` as a list. A single event contributes
        one label per date; :class:`LazyDateMap` uses this to merge
        labels across multiple sources.
        """
        norm = _normalize_date(key)
        if not isinstance(norm, datetime.date):
            return []
        self._ensure_year(norm.year)
        if super().__contains__(norm):
            return [super().__getitem__(norm)]
        return []

    def _ensure_year(self, year: int) -> None:
        if year in self._loaded_years:
            return
        for d in self._event.dates(year):
            self[d] = self._event.label_for(d, self._label_with_edition)
        self._loaded_years.add(year)


class Event:
    """One named, recurring special-event series.

    Construct one of these once per series at module scope -- see
    ``super_bowl.py`` and ``oscars.py``. Instances are immutable values.

    Parameters
    ----------
    name :
        Constant label used in the date-keyed dict by default
        (``"Super Bowl"``, ``"Academy Awards"``).
    snapshot_resource :
        ``(package_dotted_path, filename)`` passed to
        :func:`importlib.resources.files`.
    edition_label :
        Optional ``date -> str`` for the display label produced when
        ``label_with_edition=True``.
    """

    def __init__(
        self,
        name: str,
        snapshot_resource: tuple[str, str],
        edition_label: Callable[[datetime.date], str] | None = None,
    ) -> None:
        self.name = name
        self._snapshot_resource = snapshot_resource
        self._edition_label = edition_label
        self._snapshot: dict[int, list[datetime.date]] | None = None

    def _load_snapshot(self) -> dict[int, list[datetime.date]]:
        """Read and memoize the shipped JSON snapshot.

        Shape on disk: ``{"YYYY": ["YYYY-MM-DD", ...], ...}``. A list
        per year so series with multiple installments in one calendar
        year (the 2nd and 3rd Academy Awards both in 1930) round-trip
        cleanly.
        """
        if self._snapshot is None:
            package, name = self._snapshot_resource
            text = resources.files(package).joinpath(name).read_text("utf-8")
            self._snapshot = {
                int(y): [datetime.date.fromisoformat(v) for v in vs]
                for y, vs in json.loads(text).items()
            }
        return self._snapshot

    # --- module-level (year-keyed) API ------------------------------------

    def dates(self, year: int) -> list[datetime.date]:
        """All dates this series has in ``year``.

        Returns an empty list if the year is not in the shipped snapshot.
        """
        _check_year(year)
        return list(self._load_snapshot().get(year, ()))

    def first_date(self, year: int) -> datetime.date:
        """Return the (earliest) date in ``year`` or raise ``KeyError``."""
        ds = self.dates(year)
        if not ds:
            raise KeyError(
                f"{year}: not in shipped {self.name} snapshot. "
                "Upgrade special-days to pick up newly-announced dates."
            )
        return ds[0]

    def all_known(self) -> dict[int, datetime.date]:
        """Fresh ``{year: first date}`` for every year in the snapshot."""
        return {y: ds[0] for y, ds in self._load_snapshot().items()}

    def contains_date(self, d: datetime.date) -> bool:
        """``True`` iff ``d`` is one of this series' known dates."""
        if isinstance(d, datetime.datetime):
            d = d.date()
        return d in self.dates(d.year)

    # --- date-keyed (holidays-compatible) class API -----------------------

    def cls(self) -> type[_EventDict]:
        """Return a fresh ``_EventDict`` subclass bound to this event."""

        class _Specific(_EventDict):
            """Lazy date-keyed lookup; see ``special_days`` README."""

        _Specific._event = self
        _Specific.__name__ = self.name.replace(" ", "")
        _Specific.__qualname__ = _Specific.__name__
        return _Specific

    def label_for(self, d: datetime.date, with_edition: bool) -> str:
        """Display label for ``d``: constant ``name`` by default, or
        ``edition_label(d)`` when ``with_edition`` is true.
        """
        if with_edition and self._edition_label is not None:
            return self._edition_label(d)
        return self.name
