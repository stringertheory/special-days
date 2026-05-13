"""Regenerate src/special_days/data/<event>.json from Wikidata.

Usage:
    python scripts/build_snapshot.py super_bowl
    python scripts/build_snapshot.py oscars

Wikidata is the source of truth. The daily refresh workflow runs
``make snapshots`` which rebuilds every event.

Sparse overrides live in :data:`OVERRIDES` below. Add an entry when
Wikidata is wrong (vandalism, lag, transcription error) and you want
to ship a correction; remove it once Wikidata catches up. Empty in the
steady state.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from datetime import date
from pathlib import Path

# Sparse {event_name: {year: [date, ...]}} overrides merged on top of
# the Wikidata fetch. Empty values mean "trust Wikidata."
OVERRIDES: dict[str, dict[int, list[date]]] = {
    "super_bowl": {},
    "oscars": {},
}

REPO_ROOT = Path(__file__).resolve().parent.parent


def merge(
    base: dict[int, list[date]], overlay: dict[int, list[date]]
) -> dict[int, list[date]]:
    """Union dates per year; sort + dedupe."""
    out = {y: list(ds) for y, ds in base.items()}
    for y, ds in overlay.items():
        out[y] = sorted(set(out.get(y, ())) | set(ds))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "event", choices=sorted(OVERRIDES), help="event module to refresh"
    )
    parser.add_argument(
        "--out",
        default=None,
        help="output path (default: src/special_days/data/<event>.json)",
    )
    args = parser.parse_args()

    # Make the package importable from a non-installed checkout.
    sys.path.insert(0, str(REPO_ROOT / "src"))
    mod = importlib.import_module(f"special_days.{args.event}")
    from special_days.wikidata import fetch_event_dates

    data = merge(
        fetch_event_dates(mod.EVENT.wikidata_qid),
        OVERRIDES[args.event],
    )

    out_path = Path(
        args.out
        or REPO_ROOT / "src" / "special_days" / "data" / f"{args.event}.json"
    )
    payload = {
        str(y): [d.isoformat() for d in sorted(ds)]
        for y, ds in sorted(data.items())
    }
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    total = sum(len(ds) for ds in payload.values())
    print(f"wrote {total} dates across {len(payload)} years to {out_path}")


if __name__ == "__main__":
    main()
