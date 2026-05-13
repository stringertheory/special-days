# review-development.md — Maintainability and a maintenance plan

Two questions to answer:

1. **Is the project easy to keep healthy?** What does the human maintainer
   have to remember to do, and what will silently rot if forgotten?
2. **What can be automated, and where do LLM/coding agents help?**

The headline: **the project is already 80 % automated; the remaining
20 % is exactly the work that should be automated next, and most of it
fits a small CI bot.**

---

## 1. What the maintainer has to remember (today)

Drawn from the README, `Makefile`, and developer guide:

| Trigger                                  | Manual step                                                                 |
|------------------------------------------|-----------------------------------------------------------------------------|
| A new Super Bowl date is announced       | Edit `EMBEDDED` in `scripts/build_super_bowl_snapshot.py`, run `make snapshot-super-bowl`, commit `data/super_bowl.json`. |
| Wikidata updates an Oscars ceremony date | Run `make snapshot-oscars-live`, eyeball diff, commit if good.              |
| Wikidata reshapes its data model         | Live tests fail in CI on push. Update `EVENT_DATES_QUERY`, cut a release.   |
| Bug fix / new feature                    | Code, test, `make publish-patch`.                                           |
| Python release                           | Update `pyproject.toml` `requires-python`/classifiers; update CI matrix.    |
| Dependabot-style updates                 | Not configured — manual review of `astral-sh/ruff-pre-commit` rev, `actions/...@vN`, etc. |
| Wikidata returns a wrong value           | Add a hand-curated override in `EMBEDDED`; release.                         |

The list is short, which is itself a sign of taste. But every item is
"a human notices, then runs make." None of it is reactive. **The work
the maintainer is *not* doing today** is potentially the most expensive:

* No one is watching for newly-scheduled events (Super Bowl LXII was
  added some months ago; the snapshot tracks it). Cadence depends on
  the maintainer remembering to look.
* No one is watching live tests on a schedule — they fail in CI only
  on push. A query regression introduced by Wikidata last Tuesday
  doesn't break anything until the next push.
* No one is checking that the cache file format hasn't drifted from
  the snapshot file format. Today they're identical by hand; nothing
  asserts that they stay identical.

These are exactly the gaps a low-friction automation layer closes.

---

## 2. What's already done well (developer experience)

* **Editable install:** `make venv install hooks` is one command of
  setup. Excellent.
* **Test feedback loop:** `make test` finishes in 40 ms. Excellent.
* **Lint:** `ruff` + `ruff-format` via pre-commit, configured for
  `py310` target, line-length 80, select includes `E F I UP B`.
  Tasteful subset.
* **Dependency graph:** zero runtime deps, one dev dep
  (`pre-commit`). Simplest possible supply chain story.
* **CI matrix:** 6 Python versions on Linux, 2 OS extras on 3.10.
  Right-sized.
* **Release:** PyPI Trusted Publishing via OIDC; no API tokens stored
  anywhere. The `make publish-patch` target bumps version, commits,
  tags, pushes; the `Release` workflow does the rest. Modern,
  state-of-the-art.
* **Live tests:** environment-flag-gated so a flaky upstream doesn't
  break CI; manually runnable as a release-readiness check.
* **Project layout:** `src/` layout (the only correct layout for
  packages that ship data files), `py.typed` marker, `package-data`
  glob (`data/*.json`).

That's a very high baseline. Most one-person libraries I see ship
without half of this.

---

## 3. Friction points and one-time fixes

A handful of small things will compound if not addressed before the
project grows.

### 3a. `make _check_publish_ready` doesn't verify branch sync with origin

```make
@[ "$$(git rev-parse --abbrev-ref HEAD)" = "main" ] || ...
@git diff --quiet && git diff --cached --quiet || ...
```

Branch name and dirty tree are checked, but local-vs-origin is not.
A maintainer who forgot to `git pull` (or who has a stale local main)
will publish a version that doesn't include the latest remote commits.
Add:

```make
@git fetch origin main --quiet
@[ "$$(git rev-parse HEAD)" = "$$(git rev-parse origin/main)" ] || \
    { echo "local main is not at origin/main; pull or push first"; exit 1; }
```

### 3b. `uv` dependency is implicit

The release Make targets `uv version --bump`. `uv` is only checked for
in `_check_publish_ready` (good), but pulling in `uv` *just* for that
one command feels heavy. `bump-my-version` or even `sed -i` on the
pyproject would remove the dependency. Cosmetic; leave if you like
`uv`.

### 3c. No `CHANGELOG.md`

Git tags + commit messages serve as a de facto changelog, but PyPI
doesn't surface them. A `CHANGELOG.md` (or auto-generated GitHub
Releases body) makes it easy for users to know what they're getting.
Tools like `release-drafter` or `git-cliff` can auto-build one from
conventional commits.

### 3d. No `CONTRIBUTING.md`

Today contributors learn the workflow from the README's `## Tests` and
`## Maintenance` sections. A 40-line `CONTRIBUTING.md` would lift
that out, give the project a "Contribute" badge, and tell agents what
to read first.

### 3e. No `dependabot.yml` / `renovate.json`

Pre-commit hooks bump `ruff-pre-commit` rev manually
(`v0.15.12` today). GitHub Actions versions get bumped manually
(`actions/checkout@v6`, `setup-python@v6`, etc.). Both are easy to
automate; one `.github/dependabot.yml` covers it.

### 3f. The dev guide is HTML, not Markdown

Linked in the communication review. Maintenance angle: HTML doesn't
get diffed nicely in PRs, doesn't render anywhere the README does,
and discourages contribution.

### 3g. No mypy in CI

The package ships `py.typed`. Downstream type-checked users rely on
the package's annotations being right. Today nothing verifies them.
`mypy src/special_days` (default config) passes with one easy
generic-type-arg fix and one signature-narrowing fix (see
implementation review). Add a `type-check` CI job.

### 3h. No coverage in CI

`coverage` already runs locally if installed. Worth a one-time CI job
posting numbers to README badge / PR comment. Optional.

### 3i. No automated snapshot refresh

This is the biggest one. The package's *whole point* is "fresh data
without effort." Today the freshness depends on a human running
`make snapshots-live` before each release. See §5.

---

## 4. What can be automated next (ordered by ROI)

### A. **Scheduled snapshot refresh + auto-release** (highest ROI)

A nightly (or weekly) GitHub Actions workflow:

```yaml
on:
  schedule: [ cron: '0 7 * * *' ]   # 07:00 UTC daily
  workflow_dispatch: {}             # manual trigger too

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: make snapshots-live
      - id: diff
        run: |
          git diff --quiet src/special_days/data/ && echo "changed=false" >> $GITHUB_OUTPUT \
            || echo "changed=true" >> $GITHUB_OUTPUT
      - if: steps.diff.outputs.changed == 'true'
        run: SPECIAL_DAYS_LIVE_TESTS=1 python -m unittest discover -s tests -v
      - if: steps.diff.outputs.changed == 'true'
        uses: peter-evans/create-pull-request@v7
        with:
          title: "Refresh snapshots from Wikidata"
          branch: bot/refresh-snapshots
          commit-message: "Refresh snapshots from Wikidata"
          body: |
            Nightly Wikidata snapshot refresh.
            Live tests passed.
```

PR review remains human; auto-merge once the maintainer's comfortable.
This single workflow eliminates "did I remember to refresh?" entirely
and is the foundation of the architectural simplification in the
concept review.

### B. **Live-tests-only weekly cron**

Whether or not the snapshot changes, run live tests against Wikidata
once a week. Catches query-drift bugs *before* a user does.

```yaml
on:
  schedule: [ cron: '0 8 * * 1' ]   # Mondays 08:00 UTC
```

### C. **Dependabot for actions and pre-commit**

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: "/"
    schedule: { interval: weekly }
  - package-ecosystem: pip
    directory: "/"
    schedule: { interval: weekly }
```

`pre-commit-ci` (https://pre-commit.ci) is the gold standard for the
pre-commit version itself; one-line repository signup, opens auto-PRs
for hook updates.

### D. **Type-checking CI**

```yaml
type-check:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v6
    - uses: actions/setup-python@v6
      with: { python-version: "3.12" }
    - run: pip install -e ".[dev]" mypy
    - run: mypy src/special_days
```

Fix the two outstanding mypy errors first (`dict` generics on
`_Event`; `get` signature).

### E. **Coverage report on PRs**

`pytest-cov` plus `codecov` or `coverage-comment-action` posts a
delta comment per PR. Optional but nice.

### F. **`release-drafter` for CHANGELOG**

Drafts a `vX.Y.Z` release body from merged PR titles. Reduces the
"what did this release contain?" friction.

### G. **A `CITATION.cff`**

This package quotes Wikidata. A `CITATION.cff` makes it easy for
academic users to cite the package. Pure upside, fixed cost.

---

## 5. The maintenance plan I'd codify

A 12-line `MAINTENANCE.md` (or section in `CONTRIBUTING.md`) capturing:

1. **Daily.** Nothing. A bot proposes snapshot PRs; the maintainer
   reviews them when convenient.
2. **Weekly.** Glance at the Monday live-test cron. Green is no-op;
   red triggers (3).
3. **On red live tests.** Run `make snapshots-live` locally; eyeball
   the diff; if Wikidata has reshaped, update `EVENT_DATES_QUERY` in
   `_wikidata.py`; cut a patch release.
4. **On NFL/AMPAS announcement of new dates.** Either wait for the
   nightly bot to pick it up, or push the date into the relevant
   `EMBEDDED` dict and cut a patch.
5. **On new event request.** Confirm Wikidata has a Q-ID with
   well-modeled P585 statements (run the SPARQL query in the Wikidata
   web GUI). Follow the "Extending" steps in the dev guide.
6. **Before a release.** `make test` is automatic. Optionally
   `make test-live`. Then `make publish-patch`.
7. **Quarterly.** Sweep open dependabot PRs; rebase as needed.

Of those 7 items, the bot does the *noticing* on items 1–3 and the
*proposing* on 1 and 7; the human's role collapses to triage and
approval. Item 6 is the only human-initiated ritual that remains, and
even it is two `make` invocations.

---

## 6. Working with LLM/coding agents

The package is genuinely well-suited to agent maintenance, more than
most. Three reasons:

1. **Bounded scope.** Each event is a contained unit; the dev guide
   already documents the "add an event" procedure as a 7-step recipe.
2. **Self-evident failures.** When live tests fail, they tell you
   exactly which event and which property to look at.
3. **Idempotent builds.** `make snapshots-live` produces the same
   output if Wikidata hasn't changed; `make publish-patch` is the
   single release path.

### A recommended `AGENTS.md` (or `CLAUDE.md`)

A short file in the repo root spelling out:

```markdown
# Agent guide

This package is small. Conventions:

- Source of truth for the data layer is the Wikidata SPARQL query in
  `src/special_days/_wikidata.py`.
- Per-event modules in `src/special_days/<event>.py` follow a fixed
  shape (see `docs/how_it_works-developer.html` §extending).
- Tests are unit-mocked by default. Run live tests with
  `SPECIAL_DAYS_LIVE_TESTS=1 make test-live` before any release.
- Public API surface lives in `__init__.py`. Adding an event means
  touching `EVENT_REGISTRY` and `__all__`.
- Snapshot files (`src/special_days/data/*.json`) are generated; never
  edit by hand. Regenerate via `make snapshots` or `make snapshots-live`.
- Do not add runtime dependencies.
- Use `make test` for every change; `make lint` for style; `mypy
  src/special_days` for types.
- Releases: `make publish-{patch,minor,major}`. Tag push triggers
  PyPI publication.
```

Plus a 5-line `AGENT_TASKS.md` listing the half-dozen most-common
self-contained tasks an agent could pick up:

* Refresh snapshots and validate diff.
* Fix Oscars `_edition_label` off-by-one (open as of this review).
* Add World Series event (with Q-ID search step explicitly listed).
* Add a `CHANGELOG.md` entry pre-release.
* Sweep dependabot PRs.

Agents work best when the task and the verification command are both
explicit. This project naturally has both.

### Agent-suitable tasks

| Task                                      | Suitable | Why                                             |
|-------------------------------------------|----------|-------------------------------------------------|
| Snapshot refresh                          | Yes      | Pure data; tests catch drift.                   |
| Adding a new event                        | Yes      | Dev guide is a recipe.                          |
| Updating SPARQL query for schema drift    | Yes-ish  | Requires Wikidata-data-modeling judgment; agent should propose, human approves. |
| Bumping CI matrix for a new Python        | Yes      | Trivial, dependabot can do it.                  |
| Fixing test flakes                        | Yes      | No flakes in this suite today.                  |
| Refactoring `super_bowl.py` + `oscars.py` into a `_module.py` | Yes      | Bounded, well-tested change.    |
| Writing release notes                     | Yes      | Reads commit log.                               |
| Reviewing user-submitted hand-curated event data | **No** | Requires accuracy judgment; humans verify against primary sources. |

### Agent-unsuitable tasks

* Deciding whether to ship a Wikidata-vs-EMBEDDED disagreement. The
  override decision is editorial.
* Choosing which events to support next. Curatorial.
* Approving a snapshot diff that includes unexpected entries (e.g. a
  vandalized Wikidata value). Final human gate.

The pattern is: agents do *bounded mechanical* work; humans gate
*judgment* moments.

---

## 7. What will silently rot without diligence

Listing this so the maintainer (or their future agent) can audit
yearly:

* **The SPARQL query.** If Wikidata reshapes, live tests fail; without
  a weekly cron, the failure is latent until next push.
* **The shipped snapshot.** Without a refresh bot, the snapshot's
  newest date is at most as recent as the last manual release.
* **The `py.typed` claim.** Without a mypy CI job, the package can
  ship type-broken changes silently.
* **The Roman numerals beyond 399.** Tested only up to LXI.
* **The Oscars edition labels for 1931 and 1932.** Buggy today; no
  test would notice.
* **The cache atomicity guarantee.** Untested; concurrent writes can
  truncate.
* **The "cache wins over snapshot" precedence.** Documented in the
  dev guide as if obviously correct; it has a known failure mode (see
  implementation review).
* **The Wikidata User-Agent.** Computed from `__version__`. If the
  package is forked, the fork inherits *our* GitHub URL in the
  User-Agent. Forks should override.
* **Python EOL.** Python 3.10 EOL is October 2026. CI matrix today
  includes 3.10–3.15; remove 3.10 when EOL, add `3.16` when alpha.
  Dependabot doesn't do this.
* **PyPI release names.** The release-workflow's
  `actions/upload-artifact@v7` and `download-artifact@v8` pair is
  asymmetric in major version; either bump upload to v8 or downgrade
  download to v7 for symmetry. Both work today but mismatches will
  break eventually.
* **License-year.** `LICENSE` says "Copyright (c) 2026 special-days
  contributors". Auto-update or leave; either is fine, but pick a
  policy.

---

## 8. Summary scorecard

| Dimension                                  | Verdict                                              |
|--------------------------------------------|------------------------------------------------------|
| Tooling already in place                   | Strong: ruff, pre-commit, OIDC publishing, live tests |
| Workflow ergonomics for human maintainer   | High: most actions are one `make` command            |
| Coverage of the implicit maintenance ritual | Partial: no scheduled refresh, no live-test cron     |
| LLM-agent fit                              | Excellent: clear recipes, idempotent builds          |
| Documentation of the maintenance plan      | Implicit in README; should be made explicit          |
| Tendency-to-rot of unaudited surfaces      | Low-to-medium: SPARQL drift, snapshot age, mypy claims |

**The recommendation in one sentence:** add a snapshot-refresh
scheduled workflow, a weekly live-test workflow, dependabot, a mypy CI
job, and an `AGENTS.md` — then the project maintains itself for years
with human attention only at the curatorial moments.
