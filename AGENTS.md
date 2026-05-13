# Agent guide

A short orientation for LLM/coding agents working in this repository.
For humans: see [`CONTRIBUTING.md`](CONTRIBUTING.md) and
[`docs/how_it_works.md`](docs/how_it_works.md) first; this file is
about *how to operate the codebase as an agent*, not *what it does*.

## Repository conventions

* This is a small Python package — under 1000 lines of source + tests.
  Prefer touching the smallest possible diff.
* **Zero runtime dependencies** is a hard rule. The only dependency
  ever added to `[project] dependencies` would be a major design
  pivot. The `[dev]` extras can grow more freely.
* The runtime **default path is offline.** Every public function and
  every dict-like lookup answers from the shipped snapshot in
  `src/special_days/data/`. The only way the package issues an HTTPS
  request at runtime is `Event.fetch_from_wikidata()` -- an explicit
  caller opt-in. If you're adding a network call anywhere on the
  default path, stop.
* `wikidata.py` is publicly importable (for both the
  snapshot-build scripts and the opt-in runtime-refresh recipe). It
  is *not* called from `super_bowl.py` or `oscars.py`; the only
  internal reference is the lazy import inside
  `Event.fetch_from_wikidata`.
* Snapshot JSON files (`src/special_days/data/*.json`) are
  generated. Never edit by hand. Regenerate via `make snapshots`
  (Wikidata is the source of truth; sparse per-event corrections live
  in `OVERRIDES` in `scripts/build_snapshot.py`).

## Commands you should know

| Goal                              | Command |
|-----------------------------------|---------|
| Test (fast, mocked)               | `make test` |
| Test (incl. live Wikidata)        | `make test-live` |
| Lint + format check               | `make lint` |
| Type-check                        | `.venv/bin/python -m mypy src/special_days` |
| Regenerate snapshots from Wikidata | `make snapshots` |
| Cut a patch release (humans only) | `make publish-patch` |

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
* Resolving a Wikidata-vs-`EMBEDDED` disagreement. The override
  decision is editorial.
* Approving a snapshot diff that includes unexpected new entries
  (could be vandalism). Always eyeball.
* Anything that changes the public API. The package is Beta; breaking
  changes are allowed but they belong in a planned release.

## Verification

Always run `make lint test` before declaring a change done. If
touching anything in `wikidata.py` or a SPARQL string, additionally
run `SPECIAL_DAYS_LIVE_TESTS=1 make test-live` (network required).

## Style

* Comments explain *why*, not *what*. Avoid restating the code.
* Don't add backwards-compatibility shims (deprecated aliases,
  re-exports for removed names, etc.) unless explicitly asked.
* Avoid emojis in source files.
* Prefer editing existing files over creating new ones.
