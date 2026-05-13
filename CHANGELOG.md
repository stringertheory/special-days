# Changelog

Notable changes to `special-days`. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning
is [SemVer](https://semver.org/), with the caveat that pre-1.0
(Alpha) breaking changes can land on any minor release.

## [Unreleased]

Substantial rewrite. Most code that imports the package keeps working
— `SuperBowl()`, `super_bowl.date(2025)`, `union(...)`, and the
shipped snapshot all behave the same way. Code that called
`refresh()` or passed `allow_network=` needs to change; see Breaking.

### Breaking

- Runtime is offline-only. `allow_network`, `refresh()`, on-miss
  Wikidata fetch, and `WikidataUnavailable` are gone from the public
  API. Snapshots refresh in CI from Wikidata; `pip install --upgrade
  special-days` pulls new dates. To refresh mid-run, see
  `Event.fetch_from_wikidata()` below.
- Snapshot file format: `{"YYYY": "YYYY-MM-DD"}` → `{"YYYY":
  ["YYYY-MM-DD", ...]}`. The list-per-year shape lets a calendar
  year hold more than one ceremony (1930 had two Oscars).
- `EventDict` (was `_Event`) loads eagerly. `SuperBowl()` reads the
  whole snapshot at construction (microseconds). `years=[...]` is now
  a filter — the dict contains only those years — not a "preload
  these" hint.
- Modules renamed: `_event` → `event`, `_lazy` → `lazy`,
  `_wikidata` → `wikidata`, `_numerals` → `numerals`. Class
  `_EventDict` → `EventDict`. Top-level re-exports (`SuperBowl`,
  `Oscars`, `SpecialDays`, `union`, ...) unchanged. The module-level
  event instance is `EVENT` (was `_event`).
- `special_days._cache` and `~/.cache/special-days/` removed.
- `Event(...)` takes a required `wikidata_qid`. The per-event
  `fetch_super_bowl_dates` / `fetch_oscars_dates` wrappers are gone;
  callers use `fetch_event_dates(EVENT.wikidata_qid)`.

### Added

- `Event.fetch_from_wikidata()`: opt-in method returning `{year:
  [date, ...]}` from Wikidata. Recipe in `docs/how_it_works.md`.
- `dates(year) -> list[date]` on each event module, alongside
  `date(year) -> date` (which now returns the first when a year has
  more than one).
- `Event` and `EventDict` are public exports.

### Fixed

- The 3rd Academy Awards (November 5, 1930) is in the snapshot. It
  used to be dropped because the 2nd ceremony already claimed 1930.
- `Oscars(label_with_edition=True)` labels 1931 and 1932 correctly as
  "4th" and "5th" Academy Awards. The old `year - 1928` arithmetic
  produced "3rd" and "4th" because of the calendar irregularities in
  the early 1930s.
- `datetime` values now match their `.date()` in lookups instead of
  silently missing.
- Non-`int` `year` arguments raise `TypeError` instead of falling
  through to a lookup miss.
- Roman numerals are standard subtractive notation through 3999.
  Used to emit `CCCC` instead of `CD` from edition 400 on.

### Tooling and docs

- Daily CI workflow refreshes the snapshot from Wikidata and opens a
  PR if anything changed.
- Weekly CI workflow runs the live tests against Wikidata to catch
  query drift.
- `type-check` CI job; the package passes `mypy --strict`.
- Dependabot updates GitHub Actions and pip dev deps weekly.
- The two per-event build scripts collapsed into one
  `scripts/build_snapshot.py`.
- New `AGENTS.md`, `CONTRIBUTING.md`, `MAINTENANCE.md`,
  `CITATION.cff`. Developer guide is now `docs/how_it_works.md` (was
  HTML).

## [0.2.7] - 2026-05-XX

See git log.
