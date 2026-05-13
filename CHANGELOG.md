# Changelog

All notable changes to this project will be documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `Event.fetch_from_wikidata()` — opt-in method that returns the
  current ``{year: [date, ...]}`` from Wikidata. Default lookups
  remain offline; this is the explicit way for a long-running
  process to keep up with newly-announced dates without
  redeploying. See ``docs/how_it_works.md`` for the recipe.
- `special_days.wikidata` is now a public module (was `_wikidata`).
  Tests, scripts, and the new opt-in refresh path all import from
  it; the leading underscore was lying about whether external code
  could touch it.

### Changed (breaking)

- **Internal modules renamed without leading underscores.**
  `special_days._event` -> `special_days.event`,
  `special_days._lazy` -> `special_days.lazy`,
  `special_days._wikidata` -> `special_days.wikidata`,
  `special_days._numerals` -> `special_days.numerals`,
  `_EventDict` -> `EventDict`. The public re-exports from
  `special_days` are unchanged. Leading underscores remain only on
  identifiers that are genuinely implementation detail (helpers
  with single call sites, cache-state attributes, etc.).
- **`EventDict` is now eagerly populated.** Constructing
  `SuperBowl()` reads the full snapshot up front (microseconds for
  ~60-100 dates per event). `years=[...]` is now a *filter* — the
  result contains only those years — rather than a "preload, keep
  rest lazy" hint. Iteration and `len()` show every loaded date, as
  any plain `dict` would.
- **Wikidata Q-IDs moved off `_wikidata.py` onto each event.**
  `Event` now takes a required `wikidata_qid` argument; the
  per-event convenience wrappers `fetch_super_bowl_dates` and
  `fetch_oscars_dates` are gone. Scripts and live tests call
  `fetch_event_dates(super_bowl.EVENT.wikidata_qid)` instead.
- The module-level `_event` instance in each event module is now
  spelled `EVENT` (uppercase, no underscore) — adding a new event
  no longer touches the SPARQL utility module.
- **Runtime is offline-only.** Removed `allow_network`, `refresh()`,
  `WikidataUnavailable`, and the on-miss Wikidata fetch from the
  public API. Fresh data ships with new releases; a daily CI job
  rebuilds the snapshot from Wikidata and opens a PR for the
  maintainer to merge. Users who relied on the runtime refresh path
  should upgrade their release habit instead:
  `pip install --upgrade special-days`.
- **Removed:** `special_days._cache` module and the per-user cache at
  `~/.cache/special-days/`. No replacement; the snapshot inside the
  wheel is the single source of truth at runtime.
- **Snapshot file format** changed from `{"YYYY": "YYYY-MM-DD"}` to
  `{"YYYY": ["YYYY-MM-DD", ...]}`. Lists per year preserve series
  with multiple installments in one calendar year (the 2nd and 3rd
  Academy Awards both in 1930).
- `SuperBowl(allow_network=...)` constructor argument removed.
  Existing code that passed it will raise `TypeError`.

### Added

- New `dates(year) -> list[date]` function on every event module,
  alongside the existing `date(year) -> date` (which now returns the
  first date in years that have more than one).
- The 3rd Academy Awards (November 5, 1930) is now present in the
  shipped snapshot. Previously dropped because it collided with the
  2nd ceremony's calendar year under `{year: date}` semantics.
- `Oscars(label_with_edition=True)` now emits correct labels for the
  early ceremonies (1929–1934): the 2nd and 3rd Awards are
  distinguished within 1930; the 4th, 5th, and 6th line up correctly
  with 1931, 1932, and 1934.
- `datetime.datetime` keys are normalized to `datetime.date` in all
  dict-like lookups (`__contains__`, `__getitem__`, `get`,
  `get_list`), matching `holidays.HolidayBase`. Previously a
  `datetime` would silently miss a matching `date`.
- `year` arguments are type-checked: passing a `str`, `float`, `None`,
  or `bool` raises `TypeError` immediately instead of silently
  failing.
- Roman numerals now use standard subtractive notation through 3999
  (previously broke at edition 400, emitting `CCCC` instead of `CD`).
  Out-of-range values raise `ValueError`.
- `fetch_event_dates(qid)` (private API; used by snapshot scripts)
  validates that `qid` matches the `Q[1-9]\d*` pattern before
  interpolating into the SPARQL query.
- New `AGENTS.md`, `CONTRIBUTING.md`, `MAINTENANCE.md`, and
  `CITATION.cff` files documenting the maintenance workflow,
  contribution conventions, and how LLM/coding agents should engage
  with the codebase.
- Developer guide moved from HTML to Markdown
  (`docs/how_it_works.md`) and linked from the README.

### Fixed

- Oscars `_edition_label` no longer emits the wrong ordinal for the
  4th (1931) and 5th (1932) ceremonies. Previously these came back as
  "3rd" and "4th" because the naive `year - 1928` formula didn't
  account for the early-Oscars calendar irregularities.
- The shipped snapshot can no longer be silently overridden by a
  stale or tampered per-user cache file (the cache no longer exists).
- Concurrent `refresh()` calls can no longer truncate the cache file
  via interleaved writes (the cache no longer exists).

### Removed

- `super_bowl.refresh()`, `oscars.refresh()`,
  `LazyDateMap.refresh()`, and `_Event.refresh()`.
- `WikidataUnavailable` is no longer raised from the package's
  default lookup path. It still lives in `special_days.wikidata`
  for the snapshot-build scripts, the live tests, and the new
  opt-in `Event.fetch_from_wikidata()` method.
- The `_cache` module.

## [0.2.7] - 2026-05-XX

See git log.
