"""special-days: dates of named recurring events.

Ships dates for events like Super Bowl Sunday and the Academy Awards
-- the kind of date that isn't a public holiday but matters for
"what's special about today?" features. Drop-in compatible with the
`holidays <https://pypi.org/project/holidays/>`_ package via
:func:`union`.

The most common use ("is today special?"):

>>> from datetime import date
>>> from special_days import SpecialDays
>>> sd = SpecialDays()
>>> sd.get_list(date(2025, 2, 9))
['Super Bowl']
>>> sd.get_list(date(2025, 3, 2))
['Academy Awards']
>>> sd.get_list(date(2025, 5, 1))
[]

Compose with the `holidays`_ package (or any other date-keyed
mapping) via :func:`union`. The ``holidays`` side stays lazy --
years are only computed when queried:

.. _holidays: https://pypi.org/project/holidays/

>>> import holidays
>>> from special_days import union
>>> combined = union(holidays.US(), SpecialDays())
>>> combined.get_list(date(2025, 2, 9))
['Super Bowl']
>>> combined.get_list(date(2025, 7, 4))
['Independence Day']
>>> combined.get_list(date(2025, 5, 1))
[]

Two parallel APIs over the same data:

* **Year-keyed module API.** ``from special_days import super_bowl``
  then ``super_bowl.date(2025)``, ``super_bowl.dates(year)``,
  ``super_bowl.is_super_bowl_sunday(d)``, ``super_bowl.all_known()``.
  Same shape for ``oscars`` (``is_oscars_night``).

* **Date-keyed class API** (``holidays``-compatible). ``SuperBowl()``,
  ``Oscars()``, ``SpecialDays()`` are ``dict[date, str]`` subclasses
  eagerly populated from the shipped snapshot at construction.
  ``len(SuperBowl())`` is 61, iteration yields every known date, and
  ``datetime`` keys are normalized to ``date`` on lookup.

Public names exported from this package:

* :class:`SuperBowl`, :class:`Oscars` -- per-event date-keyed dict
  subclasses.
* :class:`SpecialDays` -- merged view over every shipped event, or
  a subset via ``SpecialDays(events=[...])``.
* :func:`union`, :class:`LazyDateMap` -- compose with arbitrary
  date-keyed mappings (including lazy ones like ``holidays``).
* :class:`Event`, :class:`EventDict` -- the underlying building
  blocks (used internally; relevant if you're adding a new event
  series -- see ``docs/how_it_works.md``).
* :data:`EVENT_REGISTRY` -- ``{name: dict_class}`` of shipped events.

Runtime is offline. The shipped snapshot is the single source of
truth at runtime; ``pip install --upgrade special-days`` pulls fresh
dates (snapshots are refreshed daily in CI from Wikidata). For
mid-run refresh in a long-running process, see
``super_bowl.EVENT.fetch_from_wikidata()``.

Errors at a glance:

* Unknown year -> ``KeyError`` with an "upgrade the package" hint.
* Non-``int`` year -> ``TypeError``.
* Unknown event name to ``SpecialDays(events=[...])`` -> ``ValueError``
  listing the known names.
"""

from collections.abc import Iterable
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__: str = _pkg_version("special-days")
except PackageNotFoundError:  # not installed (raw source-tree usage)
    __version__ = "0.0.0+unknown"

from .event import Event, EventDict
from .lazy import LazyDateMap, union
from .oscars import Oscars
from .super_bowl import SuperBowl

EVENT_REGISTRY: dict[str, type[EventDict]] = {
    "super_bowl": SuperBowl,
    "oscars": Oscars,
}


class SpecialDays(LazyDateMap):
    """Merged view over multiple special-day event classes.

    ``events`` accepts any mix of: registered string names
    (``"super_bowl"``), event classes (``SuperBowl``), or
    already-constructed event instances. ``None`` means "everything the
    package ships."
    """

    def __init__(
        self,
        events: Iterable[str | type[EventDict] | EventDict] | None = None,
    ) -> None:
        if events is None:
            events = list(EVENT_REGISTRY.values())
        super().__init__(*[self._resolve(e) for e in events])

    def _resolve(self, e: str | type[EventDict] | EventDict) -> EventDict:
        if isinstance(e, str):
            try:
                return EVENT_REGISTRY[e]()
            except KeyError:
                raise ValueError(
                    f"Unknown event {e!r}. Known: {sorted(EVENT_REGISTRY)}"
                ) from None
        if isinstance(e, type):
            return e()
        return e


__all__ = [
    "EVENT_REGISTRY",
    "Event",
    "EventDict",
    "LazyDateMap",
    "Oscars",
    "SpecialDays",
    "SuperBowl",
    "union",
]
