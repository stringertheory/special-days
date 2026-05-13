"""NFL Super Bowl date lookup.

    >>> from special_days import super_bowl
    >>> super_bowl.date(2025)
    datetime.date(2025, 2, 9)
    >>> super_bowl.is_super_bowl_sunday(datetime.date(2025, 2, 9))
    True

Data ships inside the wheel; ``pip install --upgrade`` pulls fresh
dates. Snapshots are refreshed in CI on a daily schedule.
"""

from __future__ import annotations

import datetime

from .event import Event

# Super Bowl I was played in 1967. The edition number for a given year
# is ``year - 1966``.
_SB_OFFSET = 1966

# Editions that don't follow the default ``"Super Bowl {roman(n)}"``
# pattern. Super Bowl 50 (2016) was officially marketed with the
# Arabic numeral. Add a row here if the league ever does it again.
_SB_OVERRIDES: dict[int, str] = {
    50: "Super Bowl 50",
}


def _roman(n: int) -> str:
    """Standard Roman numerals 1..3999."""
    if n < 1 or n > 3999:
        raise ValueError(f"_roman({n}) out of supported range 1..3999")
    table = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    out: list[str] = []
    for value, sym in table:
        while n >= value:
            out.append(sym)
            n -= value
    return "".join(out)


def _edition_label(d: datetime.date) -> str:
    n = d.year - _SB_OFFSET
    return _SB_OVERRIDES.get(n, f"Super Bowl {_roman(n)}")


EVENT = Event(
    name="Super Bowl",
    wikidata_qid="Q32096",
    snapshot_resource=("special_days.data", "super_bowl.json"),
    edition_label=_edition_label,
)

# Year-keyed functional API ------------------------------------------------


def date(year: int) -> datetime.date:
    """Return the date of the Super Bowl played in ``year``.

    Note: the Super Bowl is the championship for the previous NFL
    season. ``date(2025)`` returns Super Bowl LIX (February 9, 2025),
    which capped the 2024 NFL season.

    Raises ``KeyError`` if the year is not in the shipped snapshot.
    Upgrade the package (``pip install --upgrade special-days``) to
    pick up newly-announced dates.
    """
    return EVENT.first_date(year)


def dates(year: int) -> list[datetime.date]:
    """All known Super Bowl dates in ``year`` (always 0 or 1)."""
    return EVENT.dates(year)


def all_known() -> dict[int, datetime.date]:
    """``{year: date}`` for every Super Bowl in the shipped snapshot."""
    return EVENT.all_known()


def is_super_bowl_sunday(d: datetime.date) -> bool:
    """``True`` iff ``d`` is the date of a known Super Bowl."""
    return EVENT.contains_date(d)


# Date-keyed (holidays-compatible) class API -------------------------------

SuperBowl = EVENT.cls()
