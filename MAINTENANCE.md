# Maintenance plan

The package self-maintains for most of the year via CI. The list below
codifies what's automated, what isn't, and what a human maintainer
should look at on what cadence.

## Cadence

| Cadence    | Action                                                                                     |
|------------|--------------------------------------------------------------------------------------------|
| Daily      | `refresh-snapshots.yml` runs `make snapshots`. If the snapshot diff is non-empty and live tests pass, opens a PR on branch `bot/refresh-snapshots`. |
| Weekly     | `live-tests.yml` runs `make test-live` against the real Wikidata endpoint. Catches query drift before users do. |
| Per PR     | `ci.yml` runs the unit tests on every supported Python on Linux + macOS/Windows on the oldest supported Python, plus lint and `type-check`. |
| Per tag    | `release.yml` builds + publishes to PyPI via OIDC Trusted Publishing. |
| As needed  | Dependabot opens PRs for GitHub Actions and `pip` dependency updates. |

## What a human still does

1. **Review and merge the daily snapshot PR** when it appears. Glance
   at the diff; if anything weird shows up (a date moves backward, a
   ceremony you've never heard of appears), investigate before
   merging.
2. **Triage red weekly live-test runs.** If they go red, Wikidata
   probably reshaped its data. Update `EVENT_DATES_QUERY` in
   `wikidata.py`, cut a patch release.
3. **Cut a release after merging.** `make publish-patch` from a
   clean `main`. The release workflow handles the rest.
4. **Approve dependabot PRs** after CI passes.
5. **Add new events** when they're ready (see
   `docs/how_it_works.md`).

## What will silently rot without diligence

* The SPARQL query, if Wikidata reshapes. The weekly live-test cron
  surfaces this.
* The shipped snapshot, if the refresh workflow is disabled. The
  refresh workflow is the load-bearing piece — confirm it's running
  if it ever goes quiet.
* The `py.typed` claim, if mypy breaks. CI's `type-check` job
  surfaces this on every PR.
* Python EOL: 3.10 EOL is October 2026. Drop it from the CI matrix
  and `requires-python` when it goes. Dependabot doesn't do this.
* License year. `LICENSE` is updated on a "whenever you remember"
  basis; not load-bearing.
