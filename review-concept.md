# review-concept.md — Is `special-days` doing the right thing, the right way?

A conceptual review of the package's *premise* and its *chosen approach*.
What follows is opinionated and aimed at making this small, well-built
package better, not at validating it. The headline finding, in one
sentence: **the package is solving a real problem with a tasteful API,
but it has chosen to solve two problems where it could have solved
one — costing roughly a third of the source and nearly half the tests
to wire up a runtime freshness path that a CI bot could deliver more
reliably.**

---

## 1. Is the problem real?

Yes — and the package's framing of it is sharp.

The job-to-be-hired-for: "Given a year, tell me when the Super Bowl
(Oscars, NCAA final, …) is, with no fuss." Adjacent jobs:

* **Calendar planner.** "Build me an iCal of cultural Big Days." Today
  this requires copy-pasting from Wikipedia.
* **Date-aware UI features.** "Show a 🏈 icon on Super Bowl Sunday;
  highlight Oscars night in the weekly view." A flat
  `date → emoji` map needs a `date → label` answer first.
* **'What's special about today?' assistants.** Today this is a
  hand-curated `if today == date(...)` ladder per project.
* **`holidays`-package power users.** `holidays` deliberately excludes
  non-holiday-but-culturally-significant observances. This package
  fills exactly that gap. The `holidays`-compatible interface is the
  killer feature; it slots `special-days` into existing pipelines for
  free.

Evidence that the problem is real:

* The `holidays` package on PyPI gets 10M+ downloads/month. There is a
  large audience for "is this date significant?" libraries.
* Wikipedia's coverage of these events is excellent but unstructured;
  Wikidata's is structured but inconveniently arranged for this query
  shape (you must walk the statement graph and honor rank/precision —
  not what most callers want to do themselves).
* The events targeted (Super Bowl, Oscars, World Series Game 7, NCAA
  finals…) are exactly the ones that *aren't* algorithmically derivable
  from "second Sunday of February"-style rules. The Super Bowl's date
  rule changed in 2022 (now the second Sunday of February, not the
  first); Oscars dates shift to avoid the Winter Olympics; the World
  Series can run 4–7 games of unknown duration. Hardcoded rules don't
  cover the announced-future-event case.

So: the problem is real, the niche is well-chosen, and the existing
ecosystem doesn't already cover it. ✔

The README's framing is good but slightly undersells the most valuable
job. The killer feature is *not* `super_bowl.date(2025)` — anyone could
hardcode that. The killer feature is the **composable, lazy, lifelong**
answer to "is today special?" that survives across the years without
manual maintenance from the caller. That story deserves the first
paragraph of the README, not the back half.

---

## 2. Is the package capable of doing that job?

In its current form: largely yes, with caveats.

| Job                                  | Covered? | Notes                                                                 |
|--------------------------------------|----------|-----------------------------------------------------------------------|
| Year-keyed lookup                    | Yes      | `super_bowl.date(2025)` is exactly the right shape.                   |
| Date-keyed lookup, `holidays`-compat | Yes      | `SuperBowl()`, `SpecialDays()`, `union()`. Lazy. Mirrors `HolidayBase`.|
| Offline-first                        | Yes      | Snapshot ships in the wheel.                                          |
| Self-healing forward                 | Yes      | On unknown year, transparent Wikidata refresh + cache.                |
| Calendar export (iCal/JSON)          | **No**   | Not a one-liner; user must roll their own.                            |
| CLI                                  | **No**   | Not provided, though Makefile-level scripts exist for maintainers.    |
| Predicate composition with `holidays`| Yes      | Via `union()`, with lazy semantics preserved.                         |
| Edition-numbered display labels      | Partly   | Off-by-one for Oscars 1931–1932 (see implementation review).          |
| Future events well past the snapshot | Yes-ish  | Hit-Wikidata-on-miss works, but raises `WikidataUnavailable` offline. |
| Multi-event-per-year                 | **No**   | `setdefault` drops collisions; e.g. 3rd Academy Awards (Nov 1930) is invisible. |

The package is *competent* at its core jobs. The caveats are mostly
data-modeling decisions that are reasonable defaults but get exposed by
weird historical edges (Oscars 1928–1933) or by the eventual addition
of multi-event-per-year series (rescheduled World Series, NCAA finals
that get postponed).

---

## 3. "Doing the right thing right" — the architecture decision

This is where the package most deserves scrutiny. The current
architecture is a **three-tier hybrid**:

```
caller → snapshot (in wheel) → user cache (~/.cache) → Wikidata SPARQL
```

with a transparent fallback chain on miss. About 25 % of the package's
code (and a similar fraction of its tests) exists to wire that chain
together: `_wikidata.py` (SPARQL client + query template + error
wrapping), `_cache.py` (read/write/locate), and the per-event glue in
`super_bowl.py`/`oscars.py` (`_fetch_from_wikidata`, `all_known`,
`refresh`).

Let me enumerate the alternative designs that *could* solve the same
problem, then ask whether the chosen one is actually best.

### Alternative A — "Pure static data, push-released"

The package ships nothing but JSON, a tiny reader, and the
`holidays`-compatible class. A scheduled CI job runs
`make snapshots-live` daily (or weekly), opens a PR when the data
changes, and merges + tags a release if `make test-live` passes. Users
get fresh data via `pip install --upgrade`.

* **What's deleted:** all of `_wikidata.py` from the runtime;
  all of `_cache.py`; the `_fetch_from_wikidata`/`refresh`/`all_known`
  surface; the `allow_network` plumbing on every constructor and
  function; the `WikidataUnavailable` failure mode users have to think
  about; the `XDG_CACHE_HOME` dependency; the `User-Agent` requirement;
  the polite-rate-limiting concern; the per-process race condition on
  cache writes; the "what if the cache is corrupted" concern; the
  "should we re-fetch on miss" decision tree.
* **What's kept:** snapshot, lazy date-keyed class, `union()`,
  `EVENT_REGISTRY`, hand-curated edits to fix Wikidata, the snapshot
  build script (now run only in CI, not by end users), the live tests
  (now CI-gated, not user-gated).
* **What's lost:** end-user-driven refresh. If your installed version
  is older than the most recent announcement, lookups for the
  newly-announced year return `KeyError` until you upgrade.

### Alternative B — "Wikidata-only at runtime"

No snapshot, no cache. Every lookup queries Wikidata.

* **Pro:** always fresh; no embedded data to keep current; the smallest
  possible source code (just the SPARQL client + the class API).
* **Con:** requires network for any answer; firewalled environments
  can't use the library at all; the SPARQL endpoint becomes a runtime
  dependency; latency on every call; we become a noisy SPARQL
  consumer.
* **Verdict:** worse on the dimensions that practically matter (firewall
  reach, latency, polite-citizenship). Worth considering only if the
  package gains write-back or per-call freshness requirements that the
  current snapshot can't satisfy. Not the right choice today.

### Alternative C — "Rule-based" (where applicable)

Encode "Super Bowl = second Sunday of February" etc. as Python.

* **Pro:** no data at all.
* **Con:** the rules change (SB moved in 2022); they don't capture
  pre-rule-change years (SB I in January 1967); they don't capture
  announced-but-out-of-rule games; many events have no rule.
* **Verdict:** brittle; doesn't even fit Super Bowl cleanly, let alone
  Oscars or World Series.

### Alternative D — "Plugin to `holidays`"

PR upstream into the `holidays` package as a "non-public-holiday
observance" group.

* **Pro:** reach existing users; piggyback on `holidays`'s release
  cadence and infrastructure.
* **Con:** out of scope for `holidays`, which is explicitly about
  *legal* holidays; the maintainers would likely decline. Also loses
  the ability to evolve independently.
* **Verdict:** probably rejected; not in the package's control.

### Alternative E — current design (snapshot + per-user cache + on-miss fetch)

* **Pro:** "works offline AND always fresh." Self-healing for
  long-running scripts.
* **Con:** about 2× the code surface; introduces a per-process race
  condition (concurrent `refresh()` calls); makes the cache file part
  of the package's correctness model (any user editing
  `~/.cache/special-days/super_bowl.json` to a wrong value gets that
  wrong value back — verified during this review); makes every API
  function take an `allow_network` flag; users must reason about
  `WikidataUnavailable` *or* explicitly opt out.

### Integrative comparison

The current design solves two problems at once: "let me look this up
offline" and "let me get a freshly-announced date." But these two
problems separate cleanly:

* Offline lookup is solved by the snapshot. The snapshot is sufficient
  for >99 % of real queries (every past year, current year, and
  typically 1–2 announced future years).
* "Get a freshly-announced date" can be solved equally well by
  upgrading the package — *if* releases happen often enough.

In Zen-of-Python terms, "There should be one — and preferably only one
— obvious way to do it" is mildly violated: today there are *three*
ways to get a fresh answer (let the on-miss refresh happen; call
`refresh()` explicitly; `pip install --upgrade`). Alternative A
collapses these to one.

**The dial that tilts the recommendation is release cadence.** If
snapshots get auto-rebuilt and auto-released on Wikidata change —
realistic given the existing OIDC trusted-publishing pipeline and
`make snapshots-live` — then Alternative A is, on the merits, the
right design. The package gets smaller, simpler, more secure, less
likely to fail in production, and easier to maintain. The only loss is
the niche of "long-running script in a sandbox that needs a date
announced after install but can still reach Wikidata." That niche is
real but, judging by the data, vanishingly small: Super Bowl LXII
(2028) is the *very next* unscheduled instance, and the NFL announces
games 2–3 years out, so a once-monthly release would always be ahead
of demand.

### My integrative recommendation

A creative best-of-both: **make the snapshot the *sole* runtime
source, and move the entire Wikidata pipeline into a CI cron job that
auto-releases snapshot changes.** Concretely:

1. Delete `_wikidata.py` and `_cache.py` from the runtime path; move
   them into `scripts/` (still installable for maintainers).
2. Remove `allow_network`, `refresh()`, `WikidataUnavailable`, and the
   on-miss fetch from the public API. Unknown year → plain `KeyError`.
3. Add a daily GitHub Actions workflow that:
   * runs `make snapshots-live`,
   * if diff is non-empty, runs `make test-live`,
   * if green, commits + tags + lets the existing release workflow
     ship a new patch version.
4. Keep `EVENT_REGISTRY`, the `holidays`-compatible class, `union()`,
   `SpecialDays`. These are the actual value.
5. Document the cadence in the README: "Data is refreshed automatically
   on every Wikidata edit; `pip install --upgrade` to pull fresh
   dates."

Net effect: roughly 270 lines of source and 360 lines of tests removed
(verified by counting `_wikidata.py`, `_cache.py`, and the
`refresh`/`allow_network` plumbing in `super_bowl.py`/`oscars.py`
against the existing source tree), no user-visible regression for the
>99 % case, and the remaining 1 % case gets handled by a CI bot
instead of every end user's process.

If that recommendation is too aggressive, a softer one: keep the
current design but **demote** the network path to a documented
opt-in (`allow_network=False` default), so the production-y boring
path is always the offline one. That removes the
`WikidataUnavailable`-might-surface-on-miss footgun without throwing
away the existing code.

---

## 4. Over-engineered? Under-engineered?

In the dimensions that matter:

* **Public API surface: just right.** Two parallel APIs (year-keyed
  functional + date-keyed class) is genuinely useful, not over-engineering;
  the two answer different questions (`when is X?` vs `is today X?`).
* **Internal layering: over-engineered for the value delivered.** The
  snapshot/cache/Wikidata three-tier hierarchy is more complex than the
  problem warrants given that all three tiers are essentially the same
  data, just at different freshness. See Alternative A above.
* **Per-event modularity: under-engineered.** `super_bowl.py` and
  `oscars.py` are 90 % identical. Each new event will copy-paste another
  ~150 lines. If the package's roadmap actually includes World Series,
  NCAA, etc., this needs to collapse into a single declarative registry
  driving a single generic implementation.
* **Edition-label logic: under-thought.** Both Super Bowl and Oscars
  have year-to-edition mappings; the Oscars mapping is off-by-one for
  1931–1932 (verified live in this review). A `year → edition` table is
  a more honest representation than `edition = year - offset`.

If I were to suggest one structural change *short of* the redesign in
§3, it would be: introduce an `Event(qid, name, snapshot_path,
edition_map_or_offset)` data class with a single generic
`functional + class` implementation, and turn `super_bowl.py` and
`oscars.py` into ~15-line declarations. The existing modules already
prove this fits.

---

## 5. The Wikidata coupling — strategic risks

Wikidata is one of the most stable upstream sources available, but a
20-year horizon (the kind of horizon implied by "data sourced from
Wikidata, so it doesn't go stale") still carries real risk:

* **Property semantics drift.** P31 ("instance of"), P361 ("part of"),
  P179 ("part of the series") could be re-modeled. The `UNION` over
  all three is a good hedge, but it's not airtight.
* **Rank-and-precision conventions drift.** Today `wikibase:rank` and
  `wikibase:timePrecision` are honored; if Wikidata introduces a new
  rank tier or a new precision integer, the filter `?precision >= 11`
  might exclude or include the wrong things.
* **SPARQL endpoint deprecation.** Wikimedia has split its query
  service into "Main" and "Scholarly" endpoints; future splits could
  move our data without warning. The endpoint URL is a single constant
  in `_wikidata.py`, so the cost of fixing this is small.
* **Editor vandalism.** A single Wikidata edit could put a wrong date
  on a wrong-rank statement. The `DeprecatedRank` filter catches one
  class of this, but a *normal-rank* wrong edit would silently leak.
  The hand-curated `EMBEDDED` override in
  `scripts/build_super_bowl_snapshot.py` exists precisely for this,
  but it's a maintainer-side mitigation, not a runtime one.

Conclusion: the coupling is acceptable, the package is openly aware of
the failure modes (witness the live tests), and the maintenance plan
covers them — but only via a `make snapshots-live` ritual that a human
has to run. Automating that ritual (per §3) closes the loop.

---

## 6. Scope creep risk

The README hints at "More events to come." This is the design's most
fragile promise. Each event added under the current architecture costs:

* a new module (~150 lines, mostly duplicated)
* a new build script (~80 lines, mostly duplicated)
* a new test file (~150 lines, mostly duplicated)
* a new live test (~30 lines)
* a new JSON snapshot
* a new entry in `EVENT_REGISTRY` and `__all__`
* a new README section, snapshot, badge, etc.

That's 400–500 lines per event. Add five more events and the package
quadruples in size while doing the same thing five times over. This is
the strongest practical argument for the declarative-registry refactor
in §4.

---

## 7. The "more events" question: which ones, actually?

The README cites:
* Super Bowl ✔ shipped
* Oscars ✔ shipped
* World Series Game 7 — has 0/1/2 occurrences per year (often no
  Game 7 at all); doesn't fit the {year: date} mapping cleanly.
* NCAA championship — both men's and women's; multiple sports.

The {year: date} contract starts to break for these. The 2027 LXI
example aside, this is a design pressure that may force the package
toward a more general "named recurring event" model. Worth thinking
about *before* the second/third event ships, not after. A `{year:
list[date]}` shape inside the data layer (with the {year: date} surface
preserved as `first()`) is a cheap forward-compat move.

---

## 8. Summary scorecard

| Dimension                                    | Verdict |
|----------------------------------------------|---------|
| Problem real?                                | Yes     |
| Niche well-chosen?                           | Yes     |
| API shape (year-keyed + date-keyed)?         | Excellent |
| `holidays`-compat interop?                   | Excellent |
| Lazy / offline-first instinct?               | Excellent |
| Architecture vs. value delivered?            | **Over-built**: ~⅓ of source serves <1 % of real lookups |
| Per-event abstraction (one-of-a-kind)?       | **Under-built** — duplication will compound |
| Edition labels?                              | **Subtly wrong** for Oscars 1931–1932 |
| Wikidata coupling?                           | Acceptable, well-mitigated |
| Long-term maintainability?                   | Currently human-driven; should be cron-driven |

**Bottom line.** This is a thoughtfully-written, taste-driven small
library that has, by trying to solve "always fresh" *and* "always
offline" inside one runtime, ended up doing twice the work the user
actually needed. Three moves get it to near-perfect:

1. Collapse the freshness path into a CI release-bot
   (`make snapshots-live` on a daily cron, auto-PR, auto-merge,
   auto-release).
2. Collapse `super_bowl.py` and `oscars.py` into a declarative
   `Event(qid, name, snapshot, edition_map)` registry, so adding the
   World Series costs ~15 lines, not ~400.
3. Fix the Oscars edition labels for 1931/1932 and store internally
   as `{year: list[date]}` so the 3rd Academy Awards (Nov 1930) and
   future rescheduled-into-same-year events aren't dropped.
