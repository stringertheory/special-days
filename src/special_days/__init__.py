"""special-days: lookup dates for special events.

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

      # one merged view over many events
      sd = SpecialDays(events=["super_bowl"])
      # ... or mix with the holidays package
      combined = union(holidays.US(), sd)

Data ships inside the wheel; lookups are local and require no network.
Snapshots are refreshed in CI from Wikidata; ``pip install --upgrade``
pulls fresh data.
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
