# review-implementation.md — Bug hunt and code-quality review

Pretend the Mars mission depends on these tests passing. I ran the suite
(105 passed, 6 skipped live), `ruff check` (clean), `ruff format
--check` (clean), `mypy` (2 default-config errors, 5 with `--strict`),
`coverage` (94 % overall), `bandit` (one false-positive B310), and a
battery of hand-rolled probes (live execution, snapshot weekday-checks,
threaded/multi-process cache writes, type-confusion at the `date()`
boundary, packaged-wheel snapshot resolution, cache-poisoning, etc.).

Findings are graded:

* **🐞 BUG** — observable wrong behavior, confirmed by execution.
* **⚠️  HAZARD** — works today, but easy to break; tighten before it
  hurts.
* **🔍 SMELL** — works fine; would benefit from a redesign.

---

## 🐞 BUG-1 — Oscars edition labels off by one for 1931 and 1932

**Severity:** Medium. **Reproduced:** yes.

`special_days.oscars._edition_label(year)` computes `n = year - 1928`
and emits `f"{ordinal(n)} Academy Awards"`. This implicitly assumes
exactly one ceremony per year starting in 1929. That assumption fails
between 1930 and 1933:

| Year | Date (in snapshot) | True edition | Package emits |
|------|--------------------|--------------|---------------|
| 1929 | 1929-05-16         | 1st          | 1st ✔         |
| 1930 | 1930-04-03         | 2nd (early)  | 2nd ✔ (by luck) |
| 1930 | 1930-11-05         | 3rd (late)   | *invisible — see BUG-2* |
| 1931 | 1931-11-10         | **4th**      | **3rd ✘**     |
| 1932 | 1932-11-18         | **5th**      | **4th ✘**     |
| 1933 | (no ceremony)      | —            | —             |
| 1934 | 1934-03-16         | 6th          | 6th ✔ (resync) |
| 1949 | 1949-03-24         | 21st         | 21st ✔        |
| 2025 | 2025-03-02         | 97th         | 97th ✔        |

I verified all six rows above with the installed package; the
package indeed answers `Oscars(label_with_edition=True)[date(1931, 11,
10)]` as `"3rd Academy Awards"`. Wikipedia (and Wikidata) calls it the
4th. There are 1931- and 1932-era films legitimately tagged "for the
4th and 5th Academy Awards"; a downstream system using our label as a
key would mis-merge those.

The existing test_ordinal_corners has a comment that gives the bug
away: `# 3rd is not in our snapshot due to two-in-1930 issue; skip.`
The author noticed that 1930's two ceremonies collide but didn't
realize the collision **shifts every subsequent label by one** until
the calendar resyncs at 1934.

**Recommended fix.** Replace the `year - 1928` offset with an explicit
table for the early years:

```python
_OSCARS_EARLY = {
    1929: 1,   # 1st
    1930: 2,   # 2nd  (early-1930 ceremony — the late-1930 3rd is dropped)
    1931: 4,   # 4th  (late-1931)
    1932: 5,   # 5th  (late-1932)
    # 1933 had no ceremony
    1934: 6,   # 6th  — from here on, edition = year - 1928
}

def _edition_for(year: int) -> int:
    return _OSCARS_EARLY.get(year, year - 1928)
```

Then `_edition_label(year) = f"{_ordinal(_edition_for(year))} Academy
Awards"`. Add tests for 1931, 1932, 1934 (boundary) and 1933 (absence).

---

## 🐞 BUG-2 — The 3rd Academy Awards is invisible to the library

**Severity:** Low (one historical event, but real).
**Reproduced:** yes.

`_wikidata.parse_event_results` uses `out.setdefault(d.year, d)` so the
**earliest** date in a calendar year wins. In November 1930 the 3rd
Academy Awards was held, but the 2nd Academy Awards happened the prior
April; the November ceremony loses the year and never appears in the
snapshot or any lookup result.

A short-term fix is to overlay `EMBEDDED` in
`scripts/build_oscars_snapshot.py` with the missing 1930-11-05 date
under a synthesized key (e.g. negative-year sentinel or a renamed year
slot). But honestly: the `{year: date}` data shape is wrong for any
series that can recur within a year (rescheduled World Series, World
Cup playoffs). The structural fix is `{year: list[date]}` internally
with a `first()` adapter for the current API. See SMELL-1.

This bug is also a data-quality risk for *every* event the package will
add. The cleanest fix is structural.

---

## 🐞 BUG-3 — Cache silently overrides shipped snapshot, even when wrong

**Severity:** Medium. **Reproduced:** yes.

`all_known()` merges in the order `dict(snapshot); update(cache)`. The
cache wins on collision. Verified by writing
`{"2025": "1900-01-01"}` to `~/.cache/special-days/super_bowl.json` and
running `super_bowl.date(2025)` → returns `1900-01-01`.

Failure scenarios:

* A user (or an attacker with write access to `~/.cache/`) hand-edits
  the cache to a wrong date. Lookups return the wrong date until
  `refresh()` or `pip uninstall && reinstall`.
* Wikidata briefly serves a vandalized claim; we cache it; the
  vandalism is reverted upstream; we keep returning the bad value
  until the cache happens to be refreshed for unrelated reasons.
* A schema-broken Wikidata response slips through `parse_event_results`
  (e.g. a precision-10 placeholder if our filter regresses); the bogus
  date overrides the correct shipped value.

**Mitigation options**, in increasing order of intervention:

1. **Cheap:** for any year present in both snapshot and cache, prefer
   the cache value *only* if it is dated more recently than the
   snapshot's release date. (Requires shipping the snapshot's build
   timestamp; trivial.)
2. **Medium:** treat the shipped snapshot as authoritative for years
   the snapshot already covers; cache wins only for years the snapshot
   *doesn't* cover (i.e. cache is for *new* announcements only, never
   for *corrections*). This is the safest behavior with the smallest
   API change.
3. **Best:** remove runtime caching entirely, per the concept-review
   recommendation. Then this whole class of bug evaporates.

Whichever you pick, document the precedence in the developer guide.
Today, the dev doc says "cache wins on key collision" as if it were
obviously correct; in practice it is the cause of this bug.

---

## ⚠️  HAZARD-1 — Non-atomic cache writes, race window across processes

`_cache.write_cache` does `Path.write_text(...)`, which opens-truncate-
write-close. Two processes calling `refresh()` simultaneously can
interleave writes, producing a truncated or partially-overwritten file.
In my multi-process stress test (8 workers, 50 writes each, varying
payload sizes) I got a valid 70-entry JSON file at the end of the run,
but several intermediate states were observably short; under heavier
contention or on slower filesystems, JSON corruption is possible. The
fallback (`read_cache` → `{}` on parse failure) keeps the package
working, but every concurrent-refresh user pays a re-fetch round-trip.

**Fix.** Write to `path.with_suffix('.json.tmp')`, then
`os.replace(tmp, path)`. `os.replace` is atomic on POSIX and Windows.
The cost is one extra file syscall.

```python
def write_cache(path, data):
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {str(y): d.isoformat() for y, d in data.items()}
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True),
                       encoding='utf-8')
        os.replace(tmp, path)
    except OSError:
        pass
```

Add a test that runs writers in `multiprocessing.Pool` and asserts the
final file parses.

---

## ⚠️  HAZARD-2 — `date()` accepts non-int years and silently goes
   to the network

`super_bowl.date("2025")`, `super_bowl.date(2025.0)`, and
`super_bowl.date(None)` all dispatch through the `if year in known`
branch (returns False because the snapshot has `int` keys) and proceed
to call Wikidata. In my run they ultimately raised
`WikidataUnavailable` (sandboxed network), but in a normal environment
they'd issue a real SPARQL request and either match on a numeric coerce
(no), or `KeyError`. The user is silently charged a network round-trip
for what is a type error in their code.

**Fix.** At the top of `date()` and `_ensure_year` / `_date_lookup`,
coerce or reject:

```python
if not isinstance(year, int) or isinstance(year, bool):
    raise TypeError(f"year must be int, got {type(year).__name__}")
```

(Why exclude `bool`? `isinstance(True, int)` is True in Python.
`super_bowl.date(True)` would otherwise quietly mean `date(1)`.)

---

## ⚠️  HAZARD-3 — Roman numerals beyond `XCIX` are nonstandard

`super_bowl._roman` only carries entries up to `(100, "C")`. Beyond
edition 399 it produces nonstandard strings:

| n    | package | standard |
|------|---------|----------|
| 100  | `C`     | `C`      |
| 200  | `CC`    | `CC`     |
| 399  | `CCCXCIX` | `CCCXCIX` |
| 400  | `CCCC`  | `CD`     |
| 500  | `CCCCC` | `D`      |
| 900  | `CCCCCCCCC` | `CM` |
| 1000 | `CCCCCCCCCC` | `M` |

Super Bowl 400 falls in the year 2366. This will not bite anyone
soon, but the bug is real and trivially fixed — extend the table:

```python
table = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"),  (9, "IX"),   (5, "V"),  (4, "IV"),
    (1, "I"),
]
```

Add a property-style test that compares `_roman(n)` against a known
correct implementation for `n in range(1, 4000)`.

---

## ⚠️  HAZARD-4 — `datetime` membership silently returns False

`datetime.datetime(2025, 2, 9) in SuperBowl()` returns False, even
though the package contains the corresponding `date`. This is
*correct* dict behavior (a `datetime` hashes differently from a `date`
with the same Y/M/D), but it's a surprise that the `holidays` package
addresses by normalizing inputs. Users following the README's
"`date(2025, 2, 9) in sb`" example are fine; users feeding a
`datetime` from elsewhere silently get the wrong answer.

**Fix.** In `_Event.__contains__`/`__getitem__`/`get`/`get_list`,
normalize: `if isinstance(key, datetime): key = key.date()`. Mirrors
`holidays`. (`holidays.HolidayBase` does exactly this; the README
positions us as compatible with it.)

---

## ⚠️  HAZARD-5 — `refresh()` re-issues the SPARQL query without
   any rate-limit consideration

Wikimedia's policy is "be polite." Nothing forbids a caller from
looping `refresh()` thousands of times per minute. The package would
faithfully issue all of them with the package's User-Agent. Result:
Wikidata could blacklist the User-Agent, which would manifest as
opaque `HTTPError 429` for *every other user of the package* until the
next release bumps `__version__`.

**Fix.** Add a process-local rate limit on `_fetch_from_wikidata` — at
most one network call per minute, returning the last result on
re-entry. Or, better, remove the runtime fetch (see concept review).

---

## 🔍 SMELL-1 — `{year: date}` is the wrong internal shape

Discussed in BUG-2 and in the concept review. Internal storage should
be `{year: list[date]}` or `{year: tuple[date, ...]}`; the current API
returns `first()` and is unchanged externally. This is one strict
refactor that fixes BUG-2, BUG-1's "two ceremonies in 1930" wrinkle,
*and* future events that recur within a year (rescheduled World
Series).

---

## 🔍 SMELL-2 — Heavy duplication between `super_bowl.py` and `oscars.py`

`_load_snapshot`, `_cache_path`, `_fetch_from_wikidata`, `all_known`,
`date`, `is_X_night`/`is_X_sunday`, `refresh` are pairwise identical
modulo the snapshot path, fetcher name, and `is_X` function name.
Adding a third event will copy-paste another ~140 lines. The
existing `_Event` base captures the class API beautifully; do the same
for the module-level API by parameterizing once:

```python
# special_days/_module.py
def build_module(name, snapshot_resource, fetcher):
    def _load_snapshot(): ...
    def _cache_path(): ...
    def _fetch_from_wikidata(): ...
    def all_known(): ...
    def date(year, allow_network=True): ...
    def refresh(): ...
    return SimpleNamespace(**locals())
```

…and then `super_bowl.py` becomes ~15 lines. The `is_X_night`-style
predicate is the only true per-event bit and can live alongside the
class.

---

## 🔍 SMELL-3 — `_load_snapshot` reparses JSON on every `date()` call

Each call to `super_bowl.date(year)` reads the snapshot file from disk
and json-parses it, then merges in a freshly-read cache file. For a
single lookup this is microseconds; for code that calls `date()` in a
loop (e.g. populating a calendar for 30 years), it's wasted work and
filesystem traffic.

**Fix.** Lazy-cache the snapshot in a module-level `_SNAPSHOT` dict on
first access. Cache invalidation is not a concern because the snapshot
ships read-only inside the wheel. The cache file is small enough to
re-read each time, but it could be cached and invalidated on
`refresh()`.

---

## 🔍 SMELL-4 — `EVENT_DATES_QUERY` uses string `.format` for QID
   substitution

`EVENT_DATES_QUERY.format(qid=series_qid)` interpolates the QID into
the SPARQL string. Today all callers pass hardcoded `"Q32096"` /
`"Q19020"`. There is no real injection risk *today*, but the pattern
is fragile if `fetch_event_dates` is ever called with caller-supplied
input. Constrain at the boundary:

```python
def fetch_event_dates(series_qid: str) -> dict[int, date]:
    if not re.fullmatch(r"Q[1-9]\d*", series_qid):
        raise ValueError(f"invalid Wikidata QID: {series_qid!r}")
    ...
```

Defense in depth, cheap to add, traceable.

---

## 🔍 SMELL-5 — `_label_for(year)` in `_Event` takes a `year`
   argument it never uses

The base implementation is `return self.name`, ignoring `year`. The
parameter only matters in subclass overrides that opt into
`label_with_edition=True`. Today the signature suggests the function
inspects `year`, which is misleading for someone reading the base class
in isolation. A docstring line ("subclasses override to make
`year`-dependent labels") would close the gap.

---

## 🔍 SMELL-6 — `_event._Event` extends `dict` but never overrides
   `__setitem__` or mutating ops

A naive user can do `sb[date(2025, 2, 9)] = "nope"` and corrupt the
in-memory map. `holidays.HolidayBase` allows this too, so we're
consistent with the prior art, but inheriting from `dict` is a fragile
choice. `collections.abc.Mapping` + an inner `dict` would prevent the
mutation surface from being abused. Not urgent.

---

## 🔍 SMELL-7 — `is_super_bowl_sunday` / `is_oscars_night` default
   `allow_network=False` (good), but the year-keyed `date(year)`
   default is the opposite (`True`)

Two adjacent functions, opposite defaults. The reasoning is documented
("predicates are local-only because asking about a date you already
have is rarely a network operation"), but the inconsistency surprises
users grepping for `allow_network`. Worth a doc paragraph in the
README contrasting the two.

---

## 🔍 SMELL-8 — `_fetch_from_wikidata` only writes the cache `if fresh:`

If Wikidata returns an empty result *and* parses correctly, the cache
isn't overwritten. The comment explains this is to avoid "poisoning"
the cache with `{}` after a partial parse. Sound idea, but the *real*
"my data went away" failure mode — a successful query that drops some
years but not others — is *not* prevented. Consider also requiring a
minimum size (e.g., at least the size of the shipped snapshot) before
trusting a write.

---

## Static analysis results

* **`ruff check`** — clean, no warnings, across `src/`, `tests/`,
  `scripts/`, `examples/`.
* **`ruff format --check`** — clean.
* **`mypy` (default)** — 2 errors:
  - `_event.py:20` `Missing type arguments for generic type "dict"`.
    Easy: `class _Event(dict[date, str])`. **Fix.**
  - `_event.py:51` `Signature of "get" incompatible with supertype`.
    The override narrows the key type from `Any` to `date`. Either
    relax the override (accept `Any`/`object`) or stop inheriting from
    `dict`. **Fix worth doing** because callers passing a non-date
    today get silent `None` back; an `Any` signature would be honest.
* **`mypy --strict`** — 5 errors (the two above plus three `Any`
  returns). All fixable in <30 LOC.
* **`bandit -r src`** — one Medium "B310 audit url open for permitted
  schemes" — false positive: the URL is built from a hardcoded HTTPS
  endpoint plus a urlencoded query parameter; there is no path for a
  caller to inject a `file://` or other custom scheme. Suppress with a
  comment.
* **`coverage`** — 94 % overall, hot spots at 88 % (`oscars.py`,
  unsurprising — the non-test lines are network-fetch error branches
  that the mocked tests don't exercise end-to-end). Adequate.

---

## Security review

The package's attack surface is small:

1. **Outbound network.** `urlopen(https://query.wikidata.org/...)`
   with no proxy bypass, no credentials, no redirects. No sensitive
   data sent.
2. **Filesystem.** Reads `importlib.resources`-bundled JSON (in the
   wheel). Reads/writes a cache file under `XDG_CACHE_HOME` (or
   `~/.cache`). All writes go through `Path.write_text` to a path
   under that root; no path-traversal opportunity from external
   input.
3. **User-controllable inputs at runtime.** `year: int`,
   `allow_network: bool`, `label_with_edition: bool`,
   `events: Iterable[...]`. None of them affect the network URL, the
   cache path, or the SPARQL query body in any externally-controllable
   way. The SPARQL query template only interpolates the package's own
   hardcoded QIDs. **Net result: no SSRF/SQLi/SPARQLi vector.**
4. **Deserialization.** `json.loads` only, no `pickle`/`yaml`/`xml`.
   Parsed values are type-validated before use (`int(key)`,
   `date.fromisoformat(value)`).
5. **TLS.** Default urllib stack uses the system CA bundle and
   verifies certificates by default since Python 3.6. No insecure
   downgrades.
6. **Cache integrity.** A malicious local user with write access to
   `~/.cache/special-days/` can poison lookups (see BUG-3); the
   threat model treats `~/.cache` as trusted (consistent with most
   Python tools).
7. **Supply chain.** Zero runtime dependencies. Dev-only
   `pre-commit`. Release via PyPI Trusted Publishing (OIDC, no
   tokens). Strong posture.

I see no exploitable vulnerability. The B310 finding is a false
positive worth a `# nosec B310: hardcoded https endpoint` annotation.

---

## Summary of recommended fixes (ordered by ROI)

1. Fix Oscars `_edition_label` for 1931, 1932 (BUG-1). Trivial.
2. Make snapshot win over cache for years it already knows (BUG-3).
   ~5 LOC.
3. Atomic cache writes via tmp + `os.replace` (HAZARD-1). ~5 LOC.
4. Type-check `year` in `date()` (HAZARD-2). ~3 LOC.
5. Normalize `datetime` → `date` in `_Event` lookups (HAZARD-4).
   ~6 LOC.
6. Extend `_roman` to cover `M`/`D`/`CM`/`CD` (HAZARD-3). ~3 LOC.
7. Validate QID format before interpolation (SMELL-4). ~2 LOC.
8. Fix the two non-strict mypy errors (parametrize `dict`,
   widen `get`). ~3 LOC.

Each of these is a clean diff with a corresponding test. Together
they're well under 50 lines of source change.

Beyond those: collapse `super_bowl.py`/`oscars.py` into a parametric
`_module.py` (SMELL-2), shift to `{year: list[date]}` internally
(SMELL-1), and seriously consider the concept review's recommendation
to retire the runtime Wikidata path entirely.
