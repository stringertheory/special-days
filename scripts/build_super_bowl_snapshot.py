"""Regenerate src/special_days/data/super_bowl.json.

Two modes:

  python scripts/build_super_bowl_snapshot.py            # use embedded list
  python scripts/build_super_bowl_snapshot.py --live     # fetch Wikidata

The embedded list is what gets shipped with the package. The --live
mode is for refreshing it before a release: it queries Wikidata and
emits the same JSON shape.

The embedded list is treated as the source of truth here; if --live
disagrees, eyeball the diff before committing.

Snapshot format on disk:

    {"YYYY": ["YYYY-MM-DD", ...], ...}

Lists per year are used so that a series with multiple installments in
one calendar year (rare for Super Bowls; common in some other series)
can be represented faithfully.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# Historical Super Bowls. Sources:
# - NFL.com archives
# - Wikipedia "List of Super Bowl champions"
# Through Super Bowl LX (Feb 8, 2026)
EMBEDDED: dict[int, list[date]] = {
    1967: [date(1967, 1, 15)],  # I
    1968: [date(1968, 1, 14)],  # II
    1969: [date(1969, 1, 12)],  # III
    1970: [date(1970, 1, 11)],  # IV
    1971: [date(1971, 1, 17)],  # V
    1972: [date(1972, 1, 16)],  # VI
    1973: [date(1973, 1, 14)],  # VII
    1974: [date(1974, 1, 13)],  # VIII
    1975: [date(1975, 1, 12)],  # IX
    1976: [date(1976, 1, 18)],  # X
    1977: [date(1977, 1, 9)],  # XI
    1978: [date(1978, 1, 15)],  # XII
    1979: [date(1979, 1, 21)],  # XIII
    1980: [date(1980, 1, 20)],  # XIV
    1981: [date(1981, 1, 25)],  # XV
    1982: [date(1982, 1, 24)],  # XVI
    1983: [date(1983, 1, 30)],  # XVII
    1984: [date(1984, 1, 22)],  # XVIII
    1985: [date(1985, 1, 20)],  # XIX
    1986: [date(1986, 1, 26)],  # XX
    1987: [date(1987, 1, 25)],  # XXI
    1988: [date(1988, 1, 31)],  # XXII
    1989: [date(1989, 1, 22)],  # XXIII
    1990: [date(1990, 1, 28)],  # XXIV
    1991: [date(1991, 1, 27)],  # XXV
    1992: [date(1992, 1, 26)],  # XXVI
    1993: [date(1993, 1, 31)],  # XXVII
    1994: [date(1994, 1, 30)],  # XXVIII
    1995: [date(1995, 1, 29)],  # XXIX
    1996: [date(1996, 1, 28)],  # XXX
    1997: [date(1997, 1, 26)],  # XXXI
    1998: [date(1998, 1, 25)],  # XXXII
    1999: [date(1999, 1, 31)],  # XXXIII
    2000: [date(2000, 1, 30)],  # XXXIV
    2001: [date(2001, 1, 28)],  # XXXV
    2002: [date(2002, 2, 3)],  # XXXVI (first February game; 9/11 shift)
    2003: [date(2003, 1, 26)],  # XXXVII
    2004: [date(2004, 2, 1)],  # XXXVIII
    2005: [date(2005, 2, 6)],  # XXXIX
    2006: [date(2006, 2, 5)],  # XL
    2007: [date(2007, 2, 4)],  # XLI
    2008: [date(2008, 2, 3)],  # XLII
    2009: [date(2009, 2, 1)],  # XLIII
    2010: [date(2010, 2, 7)],  # XLIV
    2011: [date(2011, 2, 6)],  # XLV
    2012: [date(2012, 2, 5)],  # XLVI
    2013: [date(2013, 2, 3)],  # XLVII
    2014: [date(2014, 2, 2)],  # XLVIII
    2015: [date(2015, 2, 1)],  # XLIX
    2016: [date(2016, 2, 7)],  # 50
    2017: [date(2017, 2, 5)],  # LI
    2018: [date(2018, 2, 4)],  # LII
    2019: [date(2019, 2, 3)],  # LIII
    2020: [date(2020, 2, 2)],  # LIV
    2021: [date(2021, 2, 7)],  # LV
    2022: [date(2022, 2, 13)],  # LVI (first 2nd-Sunday-of-Feb game)
    2023: [date(2023, 2, 12)],  # LVII
    2024: [date(2024, 2, 11)],  # LVIII
    2025: [date(2025, 2, 9)],  # LIX
    2026: [date(2026, 2, 8)],  # LX
    2027: [date(2027, 2, 14)],  # LXI (NFL-announced; Valentine's Day)
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="fetch from Wikidata instead"
    )
    parser.add_argument(
        "--out",
        default=str(
            Path(__file__).resolve().parent.parent
            / "src/special_days/data/super_bowl.json"
        ),
    )
    args = parser.parse_args()

    if args.live:
        # Imported lazily so the script works in environments without
        # the package installed in editable mode.
        sys.path.insert(
            0,
            str(Path(__file__).resolve().parent.parent / "src"),
        )
        from special_days._wikidata import fetch_event_dates
        from special_days.super_bowl import EVENT

        data = fetch_event_dates(EVENT.wikidata_qid)
    else:
        data = EMBEDDED

    payload = {
        str(y): [d.isoformat() for d in sorted(ds)]
        for y, ds in sorted(data.items())
    }
    Path(args.out).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    total = sum(len(ds) for ds in payload.values())
    print(f"wrote {total} dates across {len(payload)} years to {args.out}")


if __name__ == "__main__":
    main()
