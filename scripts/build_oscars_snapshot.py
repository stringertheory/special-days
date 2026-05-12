"""Regenerate src/special_days/data/oscars.json.

Two modes:

  python scripts/build_oscars_snapshot.py            # use embedded list
  python scripts/build_oscars_snapshot.py --live     # fetch Wikidata

Unlike Super Bowl, the EMBEDDED list for Oscars starts empty — the
snapshot is currently bootstrapped from Wikidata via --live. Add
hand-curated entries here if Wikidata is ever wrong about a specific
date and you want to ship a correction.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Hand-curated overrides go here. Empty until needed.
EMBEDDED: dict[int, str] = {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="fetch from Wikidata instead"
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
        payload = {str(y): d.isoformat() for y, d in sorted(data.items())}
    elif EMBEDDED:
        payload = dict(sorted(EMBEDDED.items()))
    else:
        parser.error("EMBEDDED is empty; pass --live to fetch from Wikidata.")

    Path(args.out).write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"wrote {len(payload)} dates to {args.out}")


if __name__ == "__main__":
    main()
