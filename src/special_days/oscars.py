"""Academy Awards ("Oscars") ceremony date lookup.

    >>> from special_days import oscars
    >>> oscars.date(2025)
    datetime.date(2025, 3, 2)
    >>> oscars.is_oscars_night(datetime.date(2025, 3, 2))
    True

Note: the Oscars ceremony year is the year it was held, which is
usually the year after the films it honors. So ``date(2025)`` returns
the 97th Academy Awards (March 2, 2025), which awarded films released
in 2024. 1930 hosted two ceremonies (the 2nd in April and the 3rd in
November); ``date(1930)`` returns the earlier, and :func:`dates` gives
both.

Data ships inside the wheel; ``pip install --upgrade`` pulls fresh
dates. Snapshots are refreshed in CI on a daily schedule.
"""

from __future__ import annotations

import datetime

from .event import Event
from .numerals import ordinal

# Most ceremony numbers follow ``year - 1928`` -- the 1st Academy
# Awards was held May 1929, year - 1928 = 1. The exceptions are the
# early years (1930-1934), when ceremonies didn't line up 1:1 with
# calendar years: there were two ceremonies in 1930 (the 2nd in April
# and the 3rd in November), one in 1931 (the 4th), one in 1932 (the
# 5th), then no ceremony at all in 1933, and the 6th ceremony in March
# 1934. From 1934 on, the formula resyncs to ``year - 1928``.
#
# We key on the exact ceremony date so that the 2nd and 3rd Academy
# Awards -- both held in calendar year 1930 -- get distinct labels.
_OSCARS_EDITIONS: dict[datetime.date, int] = {
    datetime.date(1929, 5, 16): 1,
    datetime.date(1930, 4, 3): 2,
    datetime.date(1930, 11, 5): 3,
    datetime.date(1931, 11, 10): 4,
    datetime.date(1932, 11, 18): 5,
    # No ceremony in 1933.
    datetime.date(1934, 3, 16): 6,
    # From 1934-03-16 forward, edition = year - 1928.
}


def _edition_label(d: datetime.date) -> str:
    edition = _OSCARS_EDITIONS.get(d, d.year - 1928)
    return f"{ordinal(edition)} Academy Awards"


EVENT = Event(
    name="Academy Awards",
    wikidata_qid="Q19020",
    snapshot_resource=("special_days.data", "oscars.json"),
    edition_label=_edition_label,
)

# Year-keyed API: aliases of the Event's methods.
date = EVENT.first_date
dates = EVENT.dates
all_known = EVENT.all_known
is_oscars_night = EVENT.contains_date

# Date-keyed (holidays-compatible) class API.
Oscars = EVENT.cls()
