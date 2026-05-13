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
from typing import ClassVar, cast


def _normalize_date(key: object) -> object:
    """Coerce a ``datetime.datetime`` to its ``date`` part; pass
    everything else through unchanged. Mirrors
    ``holidays.HolidayBase`` so that a ``datetime`` from elsewhere in
    the user's code still matches.
    """
    if isinstance(key, datetime.datetime):
        return key.date()
    return key


def _check_year(year: object) -> int:
    """Reject non-``int`` years before they get further into the
    pipeline. ``bool`` is excluded explicitly because
    ``isinstance(True, int)`` is True in Python.
    """
    if isinstance(year, bool) or not isinstance(year, int):
        raise TypeError(f"year must be int, got {type(year).__name__}")
    return year


class _EventDict(dict):  # type: ignore[type-arg]
    """Lazy date-keyed dict for one event series.

    Subclasses set the ``_event`` class attribute via :meth:`Event.cls`.
    Behaves like ``dict[date, str]`` and mirrors the dict-like surface
    of `holidays.HolidayBase
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
        if years is not None:
            if isinstance(years, int) and not isinstance(years, bool):
                years = [years]
            elif isinstance(years, bool):
                raise TypeError(
                    f"years must be int or iterable of int, "
                    f"got {type(years).__name__}"
                )
            for year in years:
                self._ensure_year(_check_year(year))

    @property
    def name(self) -> str:
        return self._event.name

    def __contains__(self, key: object) -> bool:
        key = _normalize_date(key)
        if isinstance(key, datetime.date):
            self._ensure_year(key.year)
        return super().__contains__(key)

    def __getitem__(self, key: datetime.date) -> str:
        norm = _normalize_date(key)
        if isinstance(norm, datetime.date):
            self._ensure_year(norm.year)
        return cast(str, super().__getitem__(norm))

    def get(  # type: ignore[override]
        self, key: object, default: str | None = None
    ) -> str | None:
        norm = _normalize_date(key)
        if isinstance(norm, datetime.date):
            self._ensure_year(norm.year)
        return cast("str | None", super().get(norm, default))

    def get_list(self, key: object) -> list[str]:
        """All labels at ``key`` as a list. A single event contributes
        one label per date; :class:`LazyDateMap` uses this method to
        merge labels across multiple sources.
        """
        norm = _normalize_date(key)
        if isinstance(norm, datetime.date):
            self._ensure_year(norm.year)
        if super().__contains__(norm):
            return [cast(str, super().__getitem__(norm))]
        return []

    def _ensure_year(self, year: int) -> None:
        if year in self._loaded_years:
            return
        for d in self._event.dates(year):
            label = self._event.label_for(d, self._label_with_edition)
            dict.__setitem__(self, d, label)
        self._loaded_years.add(year)


class Event:
    """One named, recurring special-event series.

    Construct one of these once per series and stash it at module
    scope -- see ``super_bowl.py`` and ``oscars.py`` for examples.
    Instances are immutable values; nothing about them changes at
    runtime.

    Parameters
    ----------
    name :
        Constant label used in the date-keyed dict by default
        (``"Super Bowl"``, ``"Academy Awards"``, ...).
    snapshot_resource :
        Two-tuple of ``(package_dotted_path, filename)`` passed to
        :func:`importlib.resources.files`. Resolves to the JSON
        snapshot that ships in the wheel.
    edition_label :
        Optional callable that returns the display string for a given
        date when ``label_with_edition=True`` is requested. The
        callable takes a ``date`` and returns the label string.
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
        self._snapshot_cache: dict[int, list[datetime.date]] | None = None

    # --- snapshot loading ------------------------------------------------

    def _load_snapshot(self) -> dict[int, list[datetime.date]]:
        """Read the shipped snapshot. Memoized after first load.

        Snapshot shape on disk is
        ``{"YYYY": ["YYYY-MM-DD", ...], ...}`` (a list per year because
        a series can have multiple installments in the same calendar
        year, e.g. the 2nd and 3rd Academy Awards both in 1930).
        """
        if self._snapshot_cache is None:
            package, name = self._snapshot_resource
            text = resources.files(package).joinpath(name).read_text("utf-8")
            raw = json.loads(text)
            self._snapshot_cache = {
                int(y): [datetime.date.fromisoformat(v) for v in vs]
                for y, vs in raw.items()
            }
        # Return a shallow copy so callers can't mutate our memoized state.
        return {y: list(ds) for y, ds in self._snapshot_cache.items()}

    # --- module-level (year-keyed) API -----------------------------------

    def dates(self, year: int) -> list[datetime.date]:
        """All dates this series has in ``year``.

        Most years return a list of length 1. Returns an empty list if
        the year is not in the shipped snapshot -- the caller decides
        whether to treat that as "no event" or as "unknown".
        """
        _check_year(year)
        return list(self._load_snapshot().get(year, []))

    def first_date(self, year: int) -> datetime.date:
        """Return the first date in ``year``.

        Raises ``KeyError`` if the year is not in the shipped
        snapshot. Most series have one installment per year; for those
        with more (rare), this returns the earliest.
        """
        ds = self.dates(year)
        if not ds:
            raise KeyError(
                f"{year}: not in shipped {self.name} snapshot. "
                "Upgrade special-days to pick up newly-announced dates."
            )
        return ds[0]

    def all_known(self) -> dict[int, datetime.date]:
        """``{year: first date}`` for every year in the shipped snapshot.

        Returns a fresh dict; mutating it is harmless.
        """
        return {y: ds[0] for y, ds in self._load_snapshot().items() if ds}

    def all_known_full(self) -> dict[int, list[datetime.date]]:
        """``{year: [date, ...]}`` for every year -- preserves
        multi-installment years like 1930 for the Oscars.
        """
        return self._load_snapshot()

    def contains_date(self, d: datetime.date) -> bool:
        """``True`` iff ``d`` is one of this series' known dates."""
        if not isinstance(d, datetime.date):
            return False
        return d in self.dates(d.year)

    # --- class (date-keyed, `holidays`-compatible) API -------------------

    def cls(self) -> type[_EventDict]:
        """Return a `holidays`-compatible dict subclass for this event.

        Constructing the class instantiates a lazy dict; passing
        ``years=[...]`` eagerly loads those years.
        """

        class _Specific(_EventDict):
            __doc__ = (
                f"Lazy date-keyed lookup of {self.name} dates. "
                "Drop-in compatible with `holidays.HolidayBase "
                "<https://pypi.org/project/holidays/>`_.\n\n"
                f"See ``special_days."
                f"{self.name.lower().replace(' ', '_')}`` "
                "for the year-keyed module API over the same data; the "
                "``year`` argument means the *calendar year in which the "
                "event took place*, which for some series differs from "
                "the season or films-honored year."
            )

        _Specific._event = self
        _Specific.__name__ = self.name.replace(" ", "")
        _Specific.__qualname__ = _Specific.__name__
        return _Specific

    # --- labelling -------------------------------------------------------

    def label_for(self, d: datetime.date, with_edition: bool) -> str:
        """Display label for the date ``d``. Constant ``name`` by
        default; ``edition_label(d)`` when ``with_edition`` is true.
        """
        if with_edition and self._edition_label is not None:
            return self._edition_label(d)
        return self.name
