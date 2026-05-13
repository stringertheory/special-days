"""Emit markdown for the refresh-snapshots PR body.

For each event whose shipped snapshot diverges from HEAD, list the
changed years with:

* Wikidata item Q-ID(s) currently responsible for the year's date(s),
  linked to the item page and its revision history
* A pre-formulated Google search URL keyed on the event's filename
  stem (e.g. "Super Bowl date 1935") so the maintainer can confirm
  the date against external sources in one click

Reads new (regenerated) JSON from ``src/special_days/data/<stem>.json``
in the working tree; reads old (committed) JSON via ``git show
HEAD:<path>``. Writes markdown to stdout.

Intended for the ``refresh-snapshots`` workflow. Run manually from the
repo root after ``make snapshots`` to preview what the PR body will
look like.
"""

from __future__ import annotations

import datetime
import json
import subprocess
import urllib.parse
from pathlib import Path

from special_days import EVENT_REGISTRY
from special_days.wikidata import EVENT_DATES_QUERY, sparql_query

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "src" / "special_days" / "data"


def _parse_payload(raw: dict) -> dict[int, list[datetime.date]]:
    return {
        int(y): sorted(datetime.date.fromisoformat(d) for d in ds)
        for y, ds in raw.items()
    }


def _load_new(path: Path) -> dict[int, list[datetime.date]]:
    return _parse_payload(json.loads(path.read_text(encoding="utf-8")))


def _load_old(path: Path) -> dict[int, list[datetime.date]]:
    """HEAD version of ``path``, or ``{}`` if the file is new."""
    rel = path.relative_to(REPO_ROOT)
    try:
        text = subprocess.check_output(
            ["git", "show", f"HEAD:{rel}"], text=True
        )
    except subprocess.CalledProcessError:
        return {}
    return _parse_payload(json.loads(text))


def _diff(
    old: dict[int, list[datetime.date]],
    new: dict[int, list[datetime.date]],
) -> dict[int, dict[str, list[datetime.date]]]:
    """``{year: {"added": [...], "removed": [...]}}`` for changed years."""
    out: dict[int, dict[str, list[datetime.date]]] = {}
    for year in set(old) | set(new):
        added = sorted(set(new.get(year, [])) - set(old.get(year, [])))
        removed = sorted(set(old.get(year, [])) - set(new.get(year, [])))
        if added or removed:
            out[year] = {"added": added, "removed": removed}
    return out


def _fetch_items(
    qid: str,
) -> dict[int, list[tuple[str, str, datetime.date]]]:
    """Wikidata items currently linked to ``qid``, grouped by year.

    Returns ``{year: [(item_qid, label, date), ...]}``. Uses the same
    query the package uses to build snapshots, so the rank +
    day-precision filters are applied identically.
    """
    response = sparql_query(EVENT_DATES_QUERY.format(qid=qid))
    by_year: dict[int, list[tuple[str, str, datetime.date]]] = {}
    for b in response["results"]["bindings"]:
        raw = b.get("date", {}).get("value")
        if not raw:
            continue
        try:
            d = datetime.date.fromisoformat(raw.rstrip("Z").split("T")[0])
        except ValueError:
            continue
        item_qid = b["item"]["value"].rsplit("/", 1)[-1]
        label = b.get("itemLabel", {}).get("value", item_qid)
        by_year.setdefault(d.year, []).append((item_qid, label, d))
    return by_year


def _wikidata_link(qid: str) -> str:
    return f"https://www.wikidata.org/wiki/{qid}"


def _history_link(qid: str) -> str:
    return f"https://www.wikidata.org/w/index.php?title={qid}&action=history"


def _search_url(stem: str, year: int) -> str:
    """Pre-formulated Google search query for cross-checking.

    Example: ``oscars`` + ``2028`` -> ``https://...?q=Oscars+date+2028``.
    """
    name = stem.replace("_", " ").title()
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(
        f"{name} date {year}"
    )


def _fmt_dates(ds: list[datetime.date]) -> str:
    return ", ".join(f"`{d.isoformat()}`" for d in ds)


def _section(
    stem: str,
    diff: dict[int, dict[str, list[datetime.date]]],
    items_by_year: dict[int, list[tuple[str, str, datetime.date]]],
) -> list[str]:
    lines = [f"### {stem.replace('_', ' ').title()}", ""]
    for year in sorted(diff):
        added = diff[year]["added"]
        removed = diff[year]["removed"]
        parts = []
        if removed:
            parts.append(f"removed {_fmt_dates(removed)}")
        if added:
            parts.append(f"added {_fmt_dates(added)}")
        lines.append(f"- **{year}** — {'; '.join(parts)}")
        # Wikidata items responsible for the added dates. (Removed
        # dates aren't in Wikidata anymore, so we can't link them.)
        added_set = set(added)
        for item_qid, label, d in items_by_year.get(year, []):
            if d not in added_set:
                continue
            lines.append(
                f"  - {d.isoformat()}: "
                f'[{item_qid} "{label}"]({_wikidata_link(item_qid)}) '
                f"([history]({_history_link(item_qid)}))"
            )
        if removed and not added:
            lines.append(
                "  - Wikidata no longer reports a day-precision claim "
                "for the removed date(s); check via the search link."
            )
        lines.append(f"  - Cross-check: <{_search_url(stem, year)}>")
        lines.append("")
    return lines


def main() -> None:
    sections: list[str] = []
    for stem, dict_cls in sorted(EVENT_REGISTRY.items()):
        path = DATA_DIR / f"{stem}.json"
        old = _load_old(path)
        new = _load_new(path)
        diff = _diff(old, new)
        if not diff:
            continue
        items = _fetch_items(dict_cls.event.wikidata_qid)
        sections.extend(_section(stem, diff, items))

    print("Daily Wikidata snapshot refresh. Live tests passed.")
    print()
    if not sections:
        print("No diff against HEAD.")
        return
    print("## Changes")
    print()
    print("\n".join(sections).rstrip())
    print()
    print(
        "Eyeball the diff before merging — unexpected new entries could "
        "indicate Wikidata vandalism. Click any Wikidata link above and "
        "the **History** tab to see who last edited that item and when."
    )
    print()
    print("## To publish after merging")
    print()
    print("```bash")
    print("git pull && make publish-patch")
    print("```")
    print()
    print(
        "Bumps the patch version, commits, tags, pushes; the tag push "
        "triggers `release.yml`, which builds and OIDC-publishes to "
        "[PyPI](https://pypi.org/project/special-days/) within ~60s. "
        "Watch the release run at "
        "<https://github.com/stringertheory/special-days/actions/workflows/release.yml>."
    )


if __name__ == "__main__":
    main()
