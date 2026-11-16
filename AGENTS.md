# Agent guide

A short orientation for LLM/coding agents working in this repository.
For humans: see [`CONTRIBUTING.md`](CONTRIBUTING.md) and
[`docs/how_it_works.md`](docs/how_it_works.md) first; this file is
about *how to operate the codebase as an agent*, not *what it does*.

`special-days` is a `holidays`-compatible lookup of special-event
dates (Super Bowl and Academy Awards so far). Python 3.10+.

## Repository conventions

* This is a small Python package. Prefer touching the smallest
  possible diff.
* **Zero runtime dependencies** is a hard rule. The only dependency
  ever added to `[project] dependencies` would be a major design
  pivot. The `[dev]` extras can grow more freely.
* The runtime **default path is offline.** Every public function and
  every dict-like lookup answers from the shipped snapshot in
  `src/special_days/data/`. There is no filesystem cache. The only
  way the package issues an HTTPS request at runtime is
  `Event.fetch_from_wikidata()` -- an explicit caller opt-in. If
  you're adding a network call anywhere on the default path, stop.
* `wikidata.py` is publicly importable (for both the
  snapshot-build scripts and the opt-in runtime-refresh recipe). It
  is *not* called from `super_bowl.py` or `oscars.py`; `event.py`
  imports it, but only `Event.fetch_from_wikidata` calls into it.
* Snapshot JSON files (`src/special_days/data/*.json`) are
  generated. Never edit by hand. Regenerate via `make snapshots`
  (Wikidata is the source of truth; sparse per-event corrections live
  in `OVERRIDES` in `scripts/build_snapshot.py`).

## Commands you should know

Make targets use `.venv` when it exists, otherwise whatever is on
`PATH`.

| Goal                              | Command |
|-----------------------------------|---------|
| One-time setup                    | `make venv install hooks` |
| Test (fast, mocked)               | `make test` |
| Test (incl. live Wikidata)        | `make test-live` |
| Test one class                    | `.venv/bin/python -m unittest tests.test_super_bowl.UnknownYearTests -v` |
| Test one method                   | Append `.test_<name>` to the class path above |
| Lint + format check               | `make lint` |
| Type-check (mypy strict)          | `make type-check` |
| Regenerate snapshots (hits network) | `make snapshots`, or `make snapshot-super-bowl` / `make snapshot-oscars` |
| Cut a release (humans only)       | `make publish-patch` (or `-minor` / `-major`) |

Tests are stdlib `unittest`, not pytest. ruff runs only through
pre-commit (line length 80, rules `E/F/I/UP/B`).

## Architecture

* `event.py` holds nearly all the logic. An `Event` instance
  describes one series (name, Wikidata Q-ID, snapshot resource,
  optional edition labeller) and memoizes its snapshot in
  `Event._snapshot`. `Event.cls()` generates the date-keyed
  `EventDict` subclass.
* `super_bowl.py` / `oscars.py` are thin: an `EVENT = Event(...)`,
  the edition labeller, and module-level names bound to its methods
  (`date = EVENT.first_date`, `SuperBowl = EVENT.cls()`, ...). Because
  `date` is rebound at module scope, these modules must use
  `import datetime`, not `from datetime import date`.
* Two parallel APIs share each snapshot: year-keyed functions and
  the `holidays`-style `dict[date, str]` class. Default labels are
  the constant event name so flat `name -> emoji` lookups work;
  `label_with_edition=True` opts in to numbered display strings.
* `lazy.py`: `LazyDateMap` / `union()` forward queries to their
  sources without materializing them, which preserves the per-year
  laziness of `holidays.HolidayBase`. `SpecialDays` (in `__init__.py`)
  is a `LazyDateMap` over `EVENT_REGISTRY`.
* Snapshots are `{"YYYY": ["YYYY-MM-DD", ...]}`, a list per year
  because a year can hold several installments (two Oscars in 1930).
  `date(year)` returns the earliest, `dates(year)` all of them.
* `wikidata.py` imports `__version__` from the package, so
  `__version__` must stay defined above the `.event` import in
  `__init__.py`.
* `EVENT_DATES_QUERY` in `wikidata.py` is the most likely thing to
  break over time. The live tests exist to catch Wikidata reshaping
  its model.
* `scripts/annotate_refresh.py` finds events through
  `EVENT_REGISTRY`; `scripts/build_snapshot.py` has its own `EVENTS`
  dict, so a new event must be added to both registries.

## Testing notes

* Mock at `special_days.wikidata.urlopen`; don't reach across
  modules.
* Live tests are gated on `SPECIAL_DAYS_LIVE_TESTS=1`, which
  `make test-live` sets for you.
* `tests/test_collection.py` runs doctests for `special_days` and
  `special_days.lazy` only, so the `__init__.py` docstring is
  executable. They need `holidays`, a dev extra.

## Automation

* `refresh-snapshots.yml` (daily) runs `make snapshots` and opens a
  PR on `bot/refresh-snapshots` if the data changed and live tests
  pass. `live-tests.yml` runs weekly regardless of changes.
* `make publish-*` bumps `pyproject.toml`, tags, and pushes (requires
  `uv`, a clean `main` at `origin/main`). The tag triggers
  `release.yml`, which publishes to PyPI via OIDC.
* The README's "wikidata refreshed" badge is written by the last step
  of `refresh-snapshots.yml` to a public Gist
  (`5964c94bc8e1e539a3c47b309ca64d9f`, owner `stringertheory`) and
  rendered by shields. It is blue with the date when main matches
  Wikidata, and orange with "review pending since <date>" while a
  refresh PR is open. It needs the `GIST_BADGE_TOKEN` secret, a PAT
  with only `gist` scope. If the token expires the badge silently
  freezes, so rotate it. The CDN caches for ~5 minutes.

## Tasks that suit agents

* Snapshot refresh after a green live-test run (the scheduled CI
  workflow does this; an agent can do it ad-hoc if needed).
* Adding a new event class (follow the recipe in
  `docs/how_it_works.md#extending-adding-a-new-event-type`).
* Bumping the CI Python matrix when a new Python release ships.
* Sweeping open dependabot PRs after CI passes.
* Adding a `CHANGELOG.md` entry pre-release.
* Refactors that pass all tests and keep mypy/ruff green.

## Tasks that need a human

* Deciding which event to support next. This is curatorial.
* Resolving a disagreement between Wikidata and reality, including
  whether to add an `OVERRIDES` entry. The decision is editorial.
* Approving a snapshot diff that includes unexpected new entries
  (could be vandalism). Always eyeball.
* Anything that changes the public API. The package is Alpha;
  breaking changes are expected and explicitly OK, but the maintainer
  picks the release they go in.

## Verification

Always run `make lint test type-check` before declaring a change
done. If touching anything in `wikidata.py` or a SPARQL string,
additionally run `make test-live` (network required).

## Style

* Comments explain *why*, not *what*. Avoid restating the code.
* Don't add backwards-compatibility shims (deprecated aliases,
  re-exports for removed names, etc.) unless explicitly asked.
* Avoid emojis in source files.
* Prefer editing existing files over creating new ones.
