"""Regenerate src/special_days/data/oscars.json.

Two modes:

  python scripts/build_oscars_snapshot.py            # use EMBEDDED only
  python scripts/build_oscars_snapshot.py --live     # fetch Wikidata,
                                                     # then merge EMBEDDED

For Oscars, Wikidata is the primary source. ``EMBEDDED`` is a sparse
overlay: hand-curated entries that either correct Wikidata or plug
gaps where Wikidata hasn't caught up yet. When run with ``--live``,
the script fetches from Wikidata, then merges ``EMBEDDED`` on top --
extending the per-year date lists rather than replacing them.

Snapshot format on disk:

    {"YYYY": ["YYYY-MM-DD", ...], ...}
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# Sparse overrides applied on top of live Wikidata data when --live is
# used. Add an entry here when Wikidata is missing or wrong; remove it
# once Wikidata catches up. Empty in the steady state.
EMBEDDED: dict[int, list[date]] = {}


def _merge(
    base: dict[int, list[date]], overlay: dict[int, list[date]]
) -> dict[int, list[date]]:
    """Union dates per year; sort + dedupe."""
    out = {y: list(ds) for y, ds in base.items()}
    for y, ds in overlay.items():
        merged = set(out.get(y, ())) | set(ds)
        out[y] = sorted(merged)
    return out


def main() -> None:
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
        from special_days.oscars import EVENT
        from special_days.wikidata import fetch_event_dates

        data = _merge(fetch_event_dates(EVENT.wikidata_qid), EMBEDDED)
    elif EMBEDDED:
        data = EMBEDDED
    else:
        parser.error("EMBEDDED is empty; pass --live to fetch from Wikidata.")
        return  # unreachable, satisfies type checker

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
