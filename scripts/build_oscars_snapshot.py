"""Regenerate src/special_days/data/oscars.json.

Two modes:

  python scripts/build_oscars_snapshot.py            # use embedded list
  python scripts/build_oscars_snapshot.py --live     # fetch Wikidata,
                                                     # then overlay EMBEDDED

For Oscars, Wikidata is the primary source. EMBEDDED is a sparse
override layer: hand-curated entries that either correct Wikidata or
plug gaps where Wikidata hasn't caught up yet. When run with --live,
the script fetches Wikidata, then `update()`s the EMBEDDED entries on
top -- so a single source of truth (Wikidata) drives most of the data
but we can paper over lag without waiting for upstream.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# Sparse overrides applied on top of live Wikidata data when --live is
# used. Add an entry here when Wikidata is missing or wrong; remove it
# once Wikidata catches up.
EMBEDDED: dict[int, date] = {
    # 99th + 100th Oscars: announced by the Academy in 2025 but not yet
    # present in Wikidata as of 2026-05.
    # https://press.oscars.org/news/academy-and-abc-announce-show-dates-99th-and-100th-oscarsr
    2027: date(2027, 3, 14),  # 99th
    2028: date(2028, 3, 5),  # 100th
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="fetch from Wikidata and overlay EMBEDDED",
    )
    parser.add_argument(
        "--out",
        default=str(
            Path(__file__).resolve().parent.parent
            / "src/special_days/data/oscars.json"
        ),
    )
    args = parser.parse_args()

    if args.live:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from special_days._wikidata import fetch_oscars_dates

        data = fetch_oscars_dates()
        data.update(EMBEDDED)
    elif EMBEDDED:
        data = EMBEDDED
    else:
        parser.error("EMBEDDED is empty; pass --live to fetch from Wikidata.")

    payload = {str(y): d.isoformat() for y, d in sorted(data.items())}
    Path(args.out).write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"wrote {len(payload)} dates to {args.out}")


if __name__ == "__main__":
    main()
