"""Integer-to-text formatters used by event-edition labellers.

Kept internal (leading underscore) because the public surface should
be the labeller callable on an :class:`~special_days.event.Event`,
not these helpers directly.
"""

from __future__ import annotations

_ROMAN_TABLE: list[tuple[int, str]] = [
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


def roman(n: int) -> str:
    """Standard Roman numeral for ``n`` in the range 1..3999."""
    if n < 1 or n > 3999:
        raise ValueError(f"roman({n}) out of supported range 1..3999")
    out: list[str] = []
    for value, sym in _ROMAN_TABLE:
        while n >= value:
            out.append(sym)
            n -= value
    return "".join(out)


def ordinal(n: int) -> str:
    """English ordinal suffix: 1 -> '1st', 22 -> '22nd', 113 -> '113th'."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
