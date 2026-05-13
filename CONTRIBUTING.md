# Contributing to `special-days`

Thanks for thinking about contributing!

## Quick start

```bash
git clone https://github.com/stringertheory/special-days
cd special-days
make venv install hooks   # one-time: create venv, editable install, pre-commit
make test                 # unit tests (mocked, fast — ~50ms)
```

## Workflow

* **Lint and format** are enforced via pre-commit (`ruff` and
  `ruff-format`). `make lint` runs them across the repo.
* **Type-check** with `mypy src/special_days`. The package ships
  `py.typed`, so type changes must keep mypy green. The CI
  `type-check` job uses the default (non-strict) config.
* **Tests** use `unittest` from the standard library. Test files live
  in `tests/` and the entry point is
  `python -m unittest discover -s tests`. Mocked tests run by
  default; live tests against Wikidata are opt-in via
  `SPECIAL_DAYS_LIVE_TESTS=1 make test-live`.

## Submitting a pull request

1. Fork; create a topic branch off `main`.
2. Add tests for any new behavior. Mock at clear boundaries; don't
   reach across modules.
3. Run `make lint test`; CI runs the same.
4. Open the PR with a short description of the change and the
   reasoning (the "why", not the "what" — the diff already says
   that).

Snapshot edits land via the scheduled `Refresh snapshots` workflow.
Hand-curated entries in the `EMBEDDED` dicts inside
`scripts/build_*_snapshot.py` are appropriate when:

* an event has been announced before Wikidata picks it up, or
* Wikidata is wrong about a specific date and you want to ship a
  correction.

## Adding a new event

See [`docs/how_it_works.md`](docs/how_it_works.md) for the recipe.

## Releasing

Maintainers only. From a clean `main`:

```bash
make publish-patch       # or publish-minor / publish-major
```

This bumps the version in `pyproject.toml`, tags, and pushes; the
`release.yml` workflow then builds and publishes to PyPI via OIDC
Trusted Publishing.

## Code of Conduct

Be kind. Disagree directly with ideas, not with people. Assume good
intent.
