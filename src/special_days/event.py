"""Generic event-date lookup.

A package event series (Super Bowl, Oscars, ...) is described by an
:class:`Event` value: a constant name, the Wikidata Q-ID it was built
from, a shipped JSON snapshot of all known dates, and (optionally) a
date-keyed edition labeller. Each :class:`Event` exposes:

* a year-keyed API via :meth:`Event.first_date`, :meth:`Event.dates`,
  :meth:`Event.all_known`, and :meth:`Event.contains_date`,
* a date-keyed class API via :meth:`Event.cls`, which returns an
  eagerly-populated :class:`EventDict` subclass compatible with the
  `holidays <https://pypi.org/project/holidays/>`_ package.

Snapshots ship inside the wheel; every lookup is local and answers in
microseconds. Snapshots are refreshed in CI from Wikidata.
"""

from __future__ import annotations

import datetime
import json
from collections.abc import Callable, Iterable
from importlib import resources

from .wikidata import fetch_event_dates


def normalize_date(key: object) -> object:
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


class EventDict(dict[datetime.date, str]):
    """Date-keyed dict for one event series, eagerly populated.

    Subclasses bind to an :class:`Event` via the ``event`` class
    attribute set by :meth:`Event.cls`. Behaves like a plain
    ``dict[date, str]`` plus:

    * a :meth:`get_list` method, mirroring
      `holidays.HolidayBase.get_list
      <https://pypi.org/project/holidays/>`_,
    * automatic ``datetime`` -> ``date`` normalization on lookup,
    * an optional ``years=`` filter at construction time.
    """

    event: Event  # set by Event.cls()

    def __init__(
        self,
        years: int | Iterable[int] | None = None,
        label_with_edition: bool = False,
    ) -> None:
        super().__init__()
        if isinstance(years, int):
            years = [years]
        keep = {_check_year(y) for y in years} if years is not None else None
        for year, ds in self.event.all_known_full().items():
            if keep is not None and year not in keep:
                continue
            for d in ds:
                self[d] = self.event.label_for(d, label_with_edition)

    @property
    def name(self) -> str:
        return self.event.name

    def __contains__(self, key: object) -> bool:
        return super().__contains__(normalize_date(key))

    def __getitem__(self, key: datetime.date) -> str:
        norm = normalize_date(key)
        if not isinstance(norm, datetime.date):
            raise KeyError(key)
        return super().__getitem__(norm)

    def get(  # type: ignore[override]
        self, key: object, default: str | None = None
    ) -> str | None:
        norm = normalize_date(key)
        if not isinstance(norm, datetime.date):
            return default
        return super().get(norm, default)

    def get_list(self, key: object) -> list[str]:
        """All labels at ``key`` as a list. A single event contributes
        one label per date; :class:`LazyDateMap` uses this to merge
        labels across multiple sources.
        """
        norm = normalize_date(key)
        if not isinstance(norm, datetime.date) or norm not in self:
            return []
        return [super().__getitem__(norm)]


class Event:
    """One named, recurring special-event series.

    Construct one of these once per series at module scope -- see
    ``super_bowl.py`` and ``oscars.py``. Instances are immutable values.

    Parameters
    ----------
    name :
        Constant label used in the date-keyed dict by default
        (``"Super Bowl"``, ``"Academy Awards"``).
    wikidata_qid :
        The Wikidata item identifier for this series (e.g.
        ``"Q32096"`` for Super Bowl). Used by the snapshot-refresh
        scripts and the live tests; not consulted at runtime.
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
        wikidata_qid: str,
        snapshot_resource: tuple[str, str],
        edition_label: Callable[[datetime.date], str] | None = None,
    ) -> None:
        self.name = name
        self.wikidata_qid = wikidata_qid
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

    # --- year-keyed API ---------------------------------------------------

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

    def all_known_full(self) -> dict[int, list[datetime.date]]:
        """Fresh ``{year: [date, ...]}`` for every year. Preserves
        multi-installment years like 1930 for the Oscars.
        """
        return {y: list(ds) for y, ds in self._load_snapshot().items()}

    def contains_date(self, d: datetime.date) -> bool:
        """``True`` iff ``d`` is one of this series' known dates."""
        if isinstance(d, datetime.datetime):
            d = d.date()
        return d in self.dates(d.year)

    # --- opt-in: live refresh from Wikidata -------------------------------

    def fetch_from_wikidata(self) -> dict[int, list[datetime.date]]:
        """Fetch the current ``{year: [date, ...]}`` from Wikidata.

        Does not modify this Event's cached snapshot; the caller is
        free to use the returned data directly or assign it to
        ``self._snapshot`` to make subsequent in-process lookups see
        the fresh data. Raises
        :class:`~special_days.wikidata.WikidataUnavailable` on
        network/parse failure.

        Runtime is offline by default; calling this method is the
        explicit opt-in. See ``docs/how_it_works.md`` for the
        runtime-refresh recipe.
        """
        return fetch_event_dates(self.wikidata_qid)

    # --- date-keyed (holidays-compatible) class API -----------------------

    def cls(self) -> type[EventDict]:
        """Return a fresh :class:`EventDict` subclass bound to this event."""

        class _Specific(EventDict):
            """Date-keyed lookup; see ``special_days`` README."""

        _Specific.event = self
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
