"""special-days: lookup dates for events that disrupt normal attendance.

Two ways to use the package:

  Functional, year-keyed::

      from special_days import super_bowl
      super_bowl.date(2025)               # datetime.date(2025, 2, 9)

  ``holidays``-compatible, date-keyed::

      from datetime import date
      from special_days import SuperBowl, SpecialDays, union
      import holidays

      sb = SuperBowl()
      date(2025, 2, 9) in sb              # True
      sb[date(2025, 2, 9)]                # 'Super Bowl'

      # one merged lazy view over many events
      sd = SpecialDays(events=["super_bowl"])
      # ... or mix with the holidays package
      combined = union(holidays.US(), sd)

Data is sourced from Wikidata; a snapshot ships with the package so
lookups work offline, and a network refresh keeps the data from going
stale over the years.
"""

from collections.abc import Iterable
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__: str = _pkg_version("special-days")
except PackageNotFoundError:  # not installed (raw source-tree usage)
    __version__ = "0.0.0+unknown"

from ._event import _Event
from ._lazy import LazyDateMap, union
from .oscars import Oscars
from .super_bowl import SuperBowl

EVENT_REGISTRY: dict[str, type[_Event]] = {
    "super_bowl": SuperBowl,
    "oscars": Oscars,
}


class SpecialDays(LazyDateMap):
    """Lazy merged view over multiple special-day event classes.

    ``events`` accepts any mix of: registered string names
    (``"super_bowl"``), event classes (``SuperBowl``), or
    already-constructed event instances. ``None`` means "everything the
    package ships."
    """

    def __init__(
        self,
        events: Iterable[str | type[_Event] | _Event] | None = None,
        allow_network: bool = True,
    ) -> None:
        if events is None:
            events = list(EVENT_REGISTRY.values())
        self._allow_network: bool = allow_network
        instances = [self._resolve(e) for e in events]
        super().__init__(*instances)

    def _resolve(self, e: str | type[_Event] | _Event) -> _Event:
        if isinstance(e, str):
            try:
                cls = EVENT_REGISTRY[e]
            except KeyError:
                known = sorted(EVENT_REGISTRY)
                raise ValueError(
                    f"Unknown event {e!r}. Known: {known}"
                ) from None
            return cls(allow_network=self._allow_network)
        if isinstance(e, type):
            return e(allow_network=self._allow_network)
        return e


__all__ = [
    "EVENT_REGISTRY",
    "LazyDateMap",
    "Oscars",
    "SpecialDays",
    "SuperBowl",
    "union",
]
