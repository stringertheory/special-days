"""'What's special about today?' — composing special_days with holidays.

Demonstrates the date-keyed class API and lazy union with the third-party
``holidays`` package. Requires:

    pip install holidays

Each lookup is lazy: only the years actually queried get loaded on
either side.
"""

from datetime import date

import holidays

from special_days import SpecialDays, union

MD_HOLIDAYS = holidays.country_holidays("US", subdiv="MD")
SPECIAL = SpecialDays(events=["super_bowl"])
ALL_SPECIAL = union(MD_HOLIDAYS, SPECIAL)

EMOJI = {
    "New Year's Day": "🎉",
    "Martin Luther King Jr. Day": "🕊️",
    "Presidents' Day": "🏛️",
    "Memorial Day": "🎖️",
    "Juneteenth National Independence Day": "✊🏿",
    "Independence Day": "🎆",
    "Labor Day": "🛠️",
    "Columbus Day": "⛵️",
    "Veterans Day": "🎖️",
    "Thanksgiving Day": "🦃",
    "American Indian Heritage Day": "🪶",
    "Christmas Day": "🎄",
    "Super Bowl": "🏈",
}


def get_special(d):
    """Return all known special-day metadata for date ``d``."""
    return [
        {"name": name, "emoji": EMOJI[name]}
        for name in ALL_SPECIAL.get_list(d)
        if name in EMOJI
    ]


def main():
    today = date.today()
    sample = [
        today,
        date(today.year, 7, 4),
        date(today.year, 12, 25),
        date(2025, 2, 9),
        date(2025, 5, 1),
    ]
    for d in sample:
        hits = get_special(d)
        if hits:
            tag = ", ".join(f"{h['emoji']}  {h['name']}" for h in hits)
            print(f"{d}: {tag}")
        else:
            print(f"{d}: (nothing special)")


if __name__ == "__main__":
    main()
