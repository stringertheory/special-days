# How `special-days` works

Developer reference for the lookup pipeline, on-disk format, and the
Wikidata query used to build the shipped snapshot. Read this before
changing the data layer or adding a new event type.

## Contents

1. [What this package is (and isn't)](#what-this-package-is-and-isnt)
2. [Module layout](#module-layout)
3. [Public API surface](#public-api-surface)
4. [Date-keyed class API (`holidays`-compatible)](#date-keyed-class-api-holidays-compatible)
5. [The shipped snapshot](#the-shipped-snapshot)
6. [The Wikidata SPARQL query](#the-wikidata-sparql-query)
7. [Network policy](#network-policy)
8. [Maintenance: regenerating the snapshot](#maintenance-regenerating-the-snapshot)
9. [Extending: adding a new event type](#extending-adding-a-new-event-type)
10. [Testing model](#testing-model)

## What this package is (and isn't)

Given a year, return the date(s) on which a special event occurred (or
will occur). Currently ships the NFL Super Bowl and the Academy Awards
(Oscars). The package is intentionally tiny:

* **Zero runtime dependencies.** Only the Python standard library.
  Anything added to `[project] dependencies` in `pyproject.toml` is a
  long-term maintenance promise.
* **Offline-only at runtime.** A snapshot of all known dates ships
  inside the wheel. Lookups never touch the network.
* **Fresh by release cadence.** A scheduled CI job rebuilds the
  snapshot from Wikidata and opens a PR; the maintainer merges and the
  release pipeline ships a new patch version. `pip install --upgrade`
  pulls fresh data.

It is *not* a general calendar/holidays library. The scope is
deliberately narrow: a curated set of named, recurring events whose
official date is announced once and rarely changes.

## Module layout

```
src/special_days/
├── __init__.py          # re-exports, SpecialDays, EVENT_REGISTRY
├── super_bowl.py        # functional API + SuperBowl class
├── oscars.py            # functional API + Oscars class
├── _event.py            # generic Event + _EventDict base class
├── _lazy.py             # LazyDateMap + union (lazy view composition)
├── _wikidata.py         # SPARQL client (used by scripts/live tests only)
├── py.typed             # PEP 561 marker for downstream type checkers
└── data/
    ├── super_bowl.json  # shipped snapshot
    └── oscars.json      # shipped snapshot
scripts/
├── build_super_bowl_snapshot.py
└── build_oscars_snapshot.py
examples/
├── future_super_bowls.py
└── by_date.py
tests/
├── test_super_bowl.py     # public API
├── test_oscars.py         # public API
├── test_collection.py     # LazyDateMap, union, SpecialDays
├── test_wikidata.py       # SPARQL client (mocked)
└── test_live_wikidata.py  # opt-in, hits real Wikidata
```

Public modules are `super_bowl` and `oscars` (and future siblings).
Anything prefixed with `_` is internal: callers shouldn't depend on its
signature, and tests are free to monkeypatch it. `_wikidata.py` is in
the package only so the snapshot-build scripts can import it; it is
not used by any runtime lookup.

## Public API surface

The package exposes two parallel APIs over the same underlying data.
Pick whichever fits the question being asked.

* **Year-keyed (functional)** — per-event module
  (`special_days.super_bowl`) with `date(year)` answering "when is THIS
  year's game?" Best for planners and schedulers.
* **Date-keyed (class)** — `SuperBowl`, `SpecialDays`, `LazyDateMap`,
  all importable from `special_days`. Mirrors the [`holidays`]
  package's dict-like interface. Best for "is THIS date special?"
  composition.

[`holidays`]: https://pypi.org/project/holidays/

Every event module exposes the same four-function shape:

| Function                        | Behavior |
|---------------------------------|----------|
| `date(year)`                    | Returns the `datetime.date` of the (first) event in `year`. Raises `KeyError` if not in the shipped snapshot. Raises `TypeError` for non-`int` years. |
| `dates(year)`                   | List of all dates in `year`. Empty list if unknown. |
| `is_super_bowl_sunday(d)` (or `is_oscars_night(d)`) | Predicate over a `date`. `True` iff `d` is in the shipped snapshot. |
| `all_known()`                   | A *copy* of the `{year: first date}` mapping. Mutating the result is safe. |

There is no `refresh()` and no `allow_network`. Fresh data ships with
new releases.

## Date-keyed class API (`holidays`-compatible)

Every event also has a class form: `SuperBowl` in `super_bowl.py`,
registered in `special_days.EVENT_REGISTRY`. The class is a
`dict[date, str]` subclass that populates lazily per-year on first
access — the same shape used by `holidays.HolidayBase`.

```python
from datetime import date
from special_days import SuperBowl

sb = SuperBowl()                       # nothing loaded yet
date(2025, 2, 9) in sb                 # True; loads year 2025
sb[date(2025, 2, 9)]                   # 'Super Bowl'
sb.get_list(date(2025, 2, 9))          # ['Super Bowl']
list(sb)                               # [date(2025, 2, 9)] — only loaded keys
```

Three composition entry points layered on top:

| Symbol                              | Use case |
|-------------------------------------|----------|
| `SpecialDays(events=[...])`         | Lazy union of multiple registered events. Accepts string names, event classes, or pre-built instances. With no argument, includes everything in `EVENT_REGISTRY`. |
| `union(a, b, ...)`                  | Lazy union of arbitrary date-keyed dict-likes. Use this to mix our events with `holidays.HolidayBase` instances. |
| `LazyDateMap`                       | Read-only view returned by both of the above. Exposed primarily for type hints; users normally don't construct it directly. |

### Lazy semantics

Two rules govern all four lookup operations (`__contains__`,
`__getitem__`, `get`, `get_list`):

1. **Year-by-year.** A lookup at `date(2025, ...)` loads the entries
   for 2025 (if not already loaded) and only 2025. Each event keeps a
   `set[int]` of "years we've decided about" so a year with no
   announced date doesn't trigger repeated work.
2. **Source-by-source on union.** `LazyDateMap` walks its sources in
   order and short-circuits at the first match for `in` / `[]` /
   `get`. `get_list` visits every source so multiple labels for the
   same date are all returned. Iteration deduplicates keys across
   sources.

Critically, `for k in sd` does *not* force a load — it iterates over
the dict storage actually populated so far, which is just the years
you've already touched (or what `years=[...]` preloaded). This mirrors
`holidays.US()`'s behavior.

`datetime.datetime` keys are normalized to `datetime.date` on lookup,
so `datetime(2025, 2, 9) in sb` works the same as `date(2025, 2, 9) in
sb`.

### Labels

By default, the value for a hit is the constant event name
(`"Super Bowl"`). This is deliberate: it makes `name → emoji`-style
flat-dict lookups work without year-specific special-casing. Pass
`label_with_edition=True` on construction to get edition-numbered
labels (`"Super Bowl LIX"`) for display strings. Edition numbers are
Roman (1..3999); Super Bowl 50 (2016) is the documented
Arabic-numeral exception. For Oscars, ordinals (`"97th Academy
Awards"`) are used; the early years (1931–1932) and 1930's two
ceremonies are handled by an explicit date-keyed table because the
naive `year - 1928` formula doesn't apply there.

## The shipped snapshot

The snapshot is plain JSON, ISO dates keyed by stringified year, with
a *list* of dates per year:

```json
{
  "1929": ["1929-05-16"],
  "1930": ["1930-04-03", "1930-11-05"],
  "...": "...",
  "2025": ["2025-03-02"],
  "2026": ["2026-03-15"]
}
```

The list shape exists because a single calendar year can host multiple
installments of the same series — the 2nd and 3rd Academy Awards both
in 1930, for instance. `date(year)` returns the first; `dates(year)`
returns all.

The snapshot is bundled into the wheel via
`[tool.setuptools.package-data]` in `pyproject.toml`:

```toml
[tool.setuptools.package-data]
special_days = ["data/*.json", "py.typed"]
```

Because of the `src/` layout, "works for me in a checkout" and "works
for a user who `pip install`s" are different questions. Running tests
against the installed package (`make install && make test`) is the
canonical check.

### Two ways to regenerate

`scripts/build_super_bowl_snapshot.py` writes
`src/special_days/data/super_bowl.json` from one of two sources:

* `make snapshot-super-bowl` (no `--live`) → the `EMBEDDED` dict in
  the script. Hand-curated from NFL.com / Wikipedia. **This is the
  source of truth for the shipped Super Bowl data.** Use it when you
  want to ship a correction independent of what Wikidata currently
  says.
* `make snapshot-super-bowl-live` → fetch from Wikidata. Use this
  before a release to pick up newly-scheduled future games. Diff the
  output against the embedded list before committing; if they
  disagree, decide whose answer to ship.

Oscars uses Wikidata as the primary source; its `EMBEDDED` overlay is
a sparse list of corrections / gap-fills. See
`scripts/build_oscars_snapshot.py`.

## The Wikidata SPARQL query

The query template lives in `_wikidata.py` as `EVENT_DATES_QUERY`:

```sparql
SELECT ?item ?itemLabel ?date WHERE {
  { ?item wdt:P31  wd:{qid} . }    # instance of
  UNION
  { ?item wdt:P361 wd:{qid} . }    # part of
  UNION
  { ?item wdt:P179 wd:{qid} . }    # part of the series
  ?item p:P585 ?statement .
  ?statement psv:P585 ?dateValue .
  ?dateValue wikibase:timeValue ?date .
  ?dateValue wikibase:timePrecision ?precision .
  ?statement wikibase:rank ?rank .
  FILTER(?precision >= 11)
  FILTER(?rank != wikibase:DeprecatedRank)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
ORDER BY ?date
```

The `UNION` over three predicates is intentional: Wikidata
contributors use different relationship properties to attach an event
instance to its series, and conventions drift over time. Matching all
three gives the query the best chance of surviving a re-modeling.

The statement-level path (`p:P585` → `psv:P585`) exists to read the
`wikibase:timePrecision` qualifier. Wikidata stores P585 ("point in
time") values with a precision: `11 = day`, `10 = month`, `9 = year`.
An upcoming event announced only down to the month
(e.g. "February 2029") gets stored with precision 10 and a placeholder
day of `YYYY-MM-01`. The `FILTER(?precision >= 11)` excludes those
placeholders so they don't silently leak into results as bogus Feb-1
dates. The corresponding live test asserts every returned Super Bowl
date is a Sunday — a non-Sunday is a strong signal a precision-10
placeholder slipped through.

`?rank != wikibase:DeprecatedRank` excludes statements editors have
explicitly marked as known-wrong. Honoring rank means we don't have
to maintain per-event override lists in code; editors fix things
upstream, and our query stops returning them.

The HTTP layer (`sparql_query`) does only what's strictly necessary:

* GETs `https://query.wikidata.org/sparql?query=...` with
  `Accept: application/sparql-results+json`.
* Sends a polite `User-Agent` identifying the package and version, as
  [Wikimedia's policy] requires.
* Wraps every error — `HTTPError`, `URLError`, `TimeoutError`, decode
  failures, non-JSON bodies — in a single `WikidataUnavailable`
  exception. Callers (the build scripts and live tests) decide what
  to do.

[Wikimedia's policy]: https://meta.wikimedia.org/wiki/User-Agent_policy

`fetch_event_dates(qid)` validates that `qid` matches the
`Q[1-9]\d*` pattern before interpolating it into the SPARQL string —
defense in depth in case the function ever gets called with caller-
supplied input.

The response is parsed by `parse_event_results`, which walks the
standard [SPARQL 1.1 Query Results JSON Format] shape:

[SPARQL 1.1 Query Results JSON Format]: https://www.w3.org/TR/sparql11-results-json/

```
results.bindings[*].date.value  →  "2025-02-09T00:00:00Z"
```

The `Z` suffix is rewritten to `+00:00` so
`datetime.fromisoformat` on pre-3.11 interpreters accepts it. Within a
year, dates are deduped and sorted ascending. Two distinct ceremony
dates in the same calendar year both make it through (no
`setdefault` collapsing).

## Network policy

Runtime: **none**. Every public function and every dict-like lookup
answers from the shipped snapshot, on disk in the wheel. No
filesystem cache, no `~/.cache/special-days/`, no `XDG_CACHE_HOME`,
no proxy variables read. A user-installed package making outbound
HTTPS requests is a footgun in firewalled or sandboxed environments;
we don't.

Snapshot-build scripts: only ever invoked manually
(`make snapshots-live`) or in CI (the scheduled refresh workflow).
These do hit Wikidata. They live in `scripts/` and are not on the
user's import path under any normal installation.

## Maintenance: regenerating the snapshot

The cron-driven refresh workflow handles the steady state. A human
maintainer is involved only in three scenarios:

1. **A new game gets officially announced before Wikidata picks it
   up.** Add the date to the `EMBEDDED` dict at the top of
   `scripts/build_super_bowl_snapshot.py`, run `make snapshot-super-bowl`
   to regenerate the JSON, commit both, and `make publish-patch`.
2. **You want to verify against Wikidata before a release.** Run
   `make snapshot-super-bowl-live` (or `snapshots-live` to do both
   events), then `git diff src/special_days/data/`. If the diff is
   empty, Wikidata agrees with the embedded list. If it shows
   differences, investigate before committing.
3. **The live tests start failing.** Wikidata has probably reshaped
   its data model for that event. The first place to look is
   `EVENT_DATES_QUERY` in `_wikidata.py`. After updating, cut a new
   release.

## Extending: adding a new event type

To add, say, the World Series:

1. Find the Wikidata Q-ID for the series (verify on wikidata.org and
   that the SPARQL query, run in the Wikidata web GUI, returns dates
   at day-precision).
2. Add a thin per-event module:

   ```python
   # src/special_days/world_series.py
   import datetime
   from ._event import Event

   def _edition_label(d: datetime.date) -> str:
       return f"World Series {d.year}"

   _event = Event(
       name="World Series",
       snapshot_resource=("special_days.data", "world_series.json"),
       edition_label=_edition_label,
   )

   def date(year): return _event.first_date(year)
   def dates(year): return _event.dates(year)
   def all_known(): return _event.all_known()
   def is_world_series_game(d): return _event.contains_date(d)

   WorldSeries = _event.cls()
   ```

3. Add a thin wrapper in `_wikidata.py`:
   `fetch_world_series_dates() = fetch_event_dates("Q123456")`. The
   SPARQL query template is already general.
4. Build a snapshot: add
   `scripts/build_world_series_snapshot.py` modelled on the existing
   scripts. Run it; commit `data/world_series.json`. The
   `package-data` glob (`data/*.json`) already picks it up.
5. Register the class in `__init__.py`: add
   `"world_series": WorldSeries` to `EVENT_REGISTRY` and re-export
   `WorldSeries`.
6. Add tests mirroring the existing event tests, including a live
   test that verifies the SPARQL query against the real endpoint.

## Testing model

The test suite is intentionally layered:

* **Mocked unit tests** (`test_super_bowl.py`, `test_oscars.py`,
  `test_collection.py`, `test_wikidata.py`) run on every invocation
  of `make test`. They mock at clear boundaries; tests don't reach
  across modules to mock.
* **Live Wikidata tests** (`test_live_wikidata.py`) are gated on
  `SPECIAL_DAYS_LIVE_TESTS=1` and skip by default. Their job is to
  detect query drift: if Wikidata's modeling of the Super Bowl
  changes such that our SPARQL query no longer returns the right
  items, these tests fail loudly. Run them before cutting a release;
  the weekly live-test workflow runs them on a schedule.

Sample test invocations:

```bash
# everything fast (default)
make test

# one class
.venv/bin/python -m unittest tests.test_super_bowl.SuperBowlClassTests -v

# include live Wikidata
make test-live
```

---

References:
[SPARQL 1.1 Query Results JSON Format (W3C)](https://www.w3.org/TR/sparql11-results-json/),
[Wikimedia User-Agent policy](https://meta.wikimedia.org/wiki/User-Agent_policy),
[Q32096 (Super Bowl, Wikidata)](https://www.wikidata.org/wiki/Q32096),
[Q19020 (Academy Awards, Wikidata)](https://www.wikidata.org/wiki/Q19020).
