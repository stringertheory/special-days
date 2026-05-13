"""NFL Super Bowl date lookup.

    >>> from special_days import super_bowl
    >>> super_bowl.date(2025)
    datetime.date(2025, 2, 9)
    >>> super_bowl.is_super_bowl_sunday(datetime.date(2025, 2, 9))
    True

Note: the Super Bowl is the championship for the previous NFL season.
``date(2025)`` returns Super Bowl LIX (February 9, 2025), which capped
the 2024 NFL season.

Data ships inside the wheel; ``pip install --upgrade`` pulls fresh
dates. Snapshots are refreshed in CI on a daily schedule.
"""

from __future__ import annotations

import datetime

from .event import Event
from .numerals import roman

# Super Bowl I was played in 1967. The edition number for a given year
# is ``year - 1966``.
_SB_OFFSET = 1966

# Editions that don't follow the default ``"Super Bowl {roman(n)}"``
# pattern. Super Bowl 50 (2016) was officially marketed with the
# Arabic numeral. Add a row here if the league ever does it again.
_SB_OVERRIDES: dict[int, str] = {
    50: "Super Bowl 50",
}


def _edition_label(d: datetime.date) -> str:
    n = d.year - _SB_OFFSET
    return _SB_OVERRIDES.get(n, f"Super Bowl {roman(n)}")


EVENT = Event(
    name="Super Bowl",
    wikidata_qid="Q32096",
    snapshot_resource=("special_days.data", "super_bowl.json"),
    edition_label=_edition_label,
)

date = EVENT.first_date
dates = EVENT.dates
all_known = EVENT.all_known
is_super_bowl_sunday = EVENT.contains_date
SuperBowl = EVENT.cls()
