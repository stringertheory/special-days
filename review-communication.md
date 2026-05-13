# review-communication.md — Can a first-time visitor "get it" fast?

Roleplay: a Python developer who's heard the package mentioned, lands
on the GitHub README cold, and asks the three questions every first-time
visitor asks:

1. **Why does this exist?** (5-second test)
2. **Will it solve my problem?** (60-second test)
3. **How do I use it for *my* case?** (5-minute test)

Then I look at the rest of the surface: docstrings, examples, the
developer guide, error messages, the PyPI page.

Overall verdict: **above the bar for a small, single-author package,
and exceptionally good in places** (the dev guide is the standout) —
but the *front page* leads with mechanics before it leads with motive,
and the most charming use-case is buried.

---

## 1. The 5-second test — "Why does this exist?"

What the visitor sees in their first second on the README:

> # special-days
> Lookup dates for special events: Super Bowl Sunday, Oscars night,
> World Series Game 7, NCAA championship, etc. Data is sourced from
> Wikidata, so it doesn't go stale.
>
> Zero runtime dependencies — only the Python standard library.

This is a good opening. The list of named events does the heaviest
lifting — by the third example, the reader has internalized the scope
("oh, *these* kinds of events"). "Doesn't go stale" plants the
durability claim early. "Zero runtime dependencies" lets the
performance-/security-anxious reader exhale.

### What's missing from the 5-second answer

The visitor still doesn't know *why they'd reach for this* instead of
hardcoding a date. The single sentence that would unlock everything
is something like:

> Drop-in compatible with `holidays`, so the same `date in calendar`
> logic you use for "is today a public holiday?" also answers "is
> today Super Bowl Sunday?"

That's the killer-feature sentence and right now it's two and a half
screens down. Move it up.

### Minor 5-second nits

* "Beta. Currently supports: Super Bowl, Academy Awards (Oscars). More
  events to come." is fine but a touch defensive. Beta + a release
  cadence visible on PyPI does the same work without saying "beta."
* "Special days" is a slightly fuzzy product name. The README's first
  list (`Super Bowl Sunday, Oscars night, World Series Game 7, NCAA
  championship`) is much sharper than the name and rescues it. The
  name itself is fine; just lean on the list.

---

## 2. The 60-second test — "Will it solve my problem?"

The README's table-of-contents layout (implicit, via the `## Use`
section) is:

1. Year-keyed (planner-style)
2. Date-keyed (`holidays`-compatible)
3. Far-future years
4. Why Wikidata?
5. Cache
6. Tests
7. Maintenance
8. License

This roughly answers "will it solve my problem?" with each of the two
code blocks under §1 and §2. The two blocks are well-chosen:

```python
super_bowl.date(2025)   # → datetime.date(2025, 2, 9)
```
…and…
```python
sb = SuperBowl()
date(2025, 2, 9) in sb    # → True
```

Each is a complete, runnable example. A reader can decide in 30
seconds whether either shape fits their use case. That's excellent.

### What works in this section

* Both APIs get a code block; no hand-waving about "see the docs."
* `all_known()` is shown — useful, because it shows the *shape* of the
  internal data and signals "there's nothing magic going on."
* The `holidays` interop block is *the* example I'd lead with for
  60-second comprehension. It demonstrates the killer feature in five
  lines.
* `label_with_edition=True` is mentioned exactly once with a concrete
  example. Good.

### What I'd change

1. **Lead with the `holidays` example, not the year-keyed one.** Most
   readers landing here came from the `holidays` ecosystem. They
   already know what dict-keyed-by-date looks like; the cognitive
   handoff is one line.
2. **Add a single example near the top showing the "what's special
   about today?" pattern.** It's *the* most common real-world use,
   and it's currently only in `examples/by_date.py` where most
   first-timers won't see it. Four lines:
   ```python
   from datetime import date
   from special_days import SpecialDays
   sd = SpecialDays()
   sd.get_list(date(2025, 2, 9))   # ['Super Bowl']
   ```
3. **Show the network-fallback example with a year *more* in the
   future**, not 2035. Six years out is well within "I should ship a
   new release by then" territory; 2050 or 2075 makes the durability
   story land harder.
4. **Tighten "Why Wikidata?"** It currently reads like an internal
   design memo. Replace with one bullet ("Why Wikidata, not
   Wikipedia? Structured data, stable Q-IDs, no auth.") and link to
   the dev guide for the longer version.

---

## 3. The 5-minute test — "How do I use it for *my* case?"

Five-minute readers are trying to map the API onto their codebase.
They want signatures, type hints, error behavior, and the answer to
"can I do this offline?"

### Signatures

The README shows positional/keyword usage of every function and class
the reader needs. ✔

### Error behavior

The reader learns that unknown years raise `KeyError`. They learn
that `allow_network=False` causes a `KeyError` instead of a network
attempt. They are *not* told that `refresh()` raises `RuntimeError`
when `allow_network=False`, nor that an in-flight `date(unknown_year)`
can raise `WikidataUnavailable` if the network is down. Both
exceptions are documented in docstrings, but the README is silent.

For a library whose docstring says "doesn't go stale" partly *because*
of a network fallback, the failure mode of that fallback is something
the README has to call out. A two-sentence subsection:

> Network failures raise `WikidataUnavailable` from
> `special_days._wikidata`. Use `allow_network=False` to keep lookups
> strictly offline.

…fixes it.

### Offline-first

The "Far-future years" section is the one a network-anxious reader
will read carefully. It does the right job. One subtle gap: the
section title implies the network fallback is only for "far future"
queries, but it actually triggers for *any* year not in the shipped
snapshot — including the historical years that aren't in our list (we
filter the early Oscars heavily). Re-title to "Years not in the
shipped snapshot" or similar.

### Discoverability of `SpecialDays`

`SpecialDays` is the most powerful thing in the package — a single
lazy union of every event the package knows. It appears in code
blocks but never gets a section header. A new reader trying to do
"all special days" has to read between the lines. Promote it.

---

## 4. The docstrings (the source-of-truth secondary docs)

Generally excellent. Notable strengths:

* Module-level docstrings open with a runnable example (`>>>`). I
  copied a few into a Python prompt and they all worked.
* The "Why" comments in `_wikidata.py` are some of the best inline
  prose I've reviewed: they explain the SPARQL choices (P31/P361/P179
  union, precision filter, deprecated-rank filter) at the level a
  future maintainer needs.
* The `__init__.py` module docstring is exactly the right size for
  `help(special_days)` output.

Minor issues:

* `_Event` docstrings reference "holidays-compatible" but never link
  out to the `holidays` package. A `:py:class:` Sphinx ref or a plain
  URL would help. (The README does link, but the docstring is what a
  reader sees in IPython.)
* `super_bowl.date()`'s docstring explains the "Super Bowl played in
  the given year" semantics very clearly. The `oscars.date()` one is
  good too. But there's no equivalent note on `SuperBowl(years=...)`
  — a reader who arrives at the class without reading the function
  first might trip on "I asked for 2024 but got 2025-02-09."
  Restate the convention briefly on the class docstring.
* `SpecialDays.__init__` has a nicely worded docstring; consider
  copying its example into the README.
* `LazyDateMap`'s doctest is marked `# doctest: +SKIP` because it
  imports `holidays`. The doctest never runs in CI. Consider either
  installing `holidays` in the test environment and dropping `+SKIP`,
  or rewriting it to use a plain dict so it actually executes.

---

## 5. The developer guide (`docs/how_it_works-developer.html`)

This is the document that elevates the project from "small library" to
"taught library." It's roughly 600 lines of carefully written HTML,
includes an ASCII diagram of the three-tier lookup, a behavior matrix
of all network scenarios, and step-by-step instructions for adding a
new event. Genuinely useful prose.

### Strengths

* Concrete: every section can be followed without reading code.
* The "lifecycle of a `date(year)` call" walkthrough is exactly what a
  new maintainer needs.
* The "extending: adding a new event type" section is clear enough
  that an LLM agent could follow it (and should — see the development
  review).
* The behavior matrix in §Network policy is the single best piece of
  documentation in the project. Move a condensed version of it to the
  README too.

### Weaknesses

* **It's HTML, not Markdown.** The README is rendered by GitHub
  (Markdown); the dev guide is a static HTML file you have to clone
  the repo to view comfortably. There's no link from README → dev
  guide, no GitHub Pages publication, no "build the docs" instruction.
  Either flip it to `docs/how_it_works-developer.md` and link from
  README, or publish via GitHub Pages and link.
* The HTML hand-styles dark mode with `@media (prefers-color-scheme:
  dark)`, which is charming but completely undone by `github.io`
  themes. Drop the styling, let the host theme it.
* The doc claims "the SPARQL query template is already general" in
  the "Extending" section. True today; mention `Q19020` (Oscars)
  required no template changes, as evidence.

---

## 6. Examples

Both examples (`future_super_bowls.py`, `by_date.py`) are short, well
commented, and illustrate distinct use cases. `by_date.py`'s
emoji-by-name pattern is so cute it should be in the README — that's
the example a reader screenshots and tweets.

One missing example: how to **bulk-populate** a year range
efficiently. Today, `SuperBowl(years=range(1967, 2030))` would
preload every year and answer membership instantly. This isn't shown
anywhere; it's the right pattern for a calendar pre-build.

---

## 7. Error messages

I exercised the error paths:

* `SpecialDays(events=["world_cup"])` →
  `ValueError("Unknown event 'world_cup'. Known: ['oscars',
  'super_bowl']")` — *excellent*. Includes the offending name and
  the full set of valid alternatives.
* `super_bowl.date(2099, allow_network=False)` → `KeyError: 2099` —
  fine. The plain integer is enough.
* `oscars.refresh()` with `allow_network=False` (via `Oscars` instance)
  → `RuntimeError("Oscars.refresh() requires network access, but this
  instance was constructed with allow_network=False.")` — *good*.
  Names the class, names the constructor flag, explains why.
* `WikidataUnavailable("HTTP Error 503: Service Unavailable")` —
  inherited from the underlying exception, useful enough.

No error message is hostile. One could be sharper: the `KeyError`
from `date(unknown_year)` could include "(year not in shipped snapshot
or local cache; allow_network was False)" so the user understands
*why* it's a miss. Right now the `KeyError` and the
`WikidataUnavailable`-wrapped `KeyError` look identical from outside,
which complicates debugging.

---

## 8. The PyPI page

Inherits from `pyproject.toml`:

* **Description.** "Lookup dates for special events (Super Bowl,
  Oscars, ...) using Wikidata as the source of truth." — fine,
  slightly more dry than the README's opening but acceptable.
* **Classifiers.** Beta status, Python 3.10–3.14 all declared,
  `Topic :: Office/Business :: Scheduling` is a stretch — *Calendar*
  isn't a separate top-level classifier but `Office/Business
  :: Scheduling` and `Topic :: Software Development :: Libraries`
  would both make sense. Worth adding `Libraries`.
* **Keywords.** `["super bowl", "oscars", "events", "wikidata",
  "calendar"]` — good; add `"holidays"` so the `holidays` ecosystem
  discovers us.
* **Project URLs.** Just Homepage. Add `Documentation`,
  `Source`, `Changelog`, `Tracker`.

These are 30-second edits in `pyproject.toml`.

---

## 9. Delight

A library's delight comes from small touches that say "the author
respects you." This package has them:

* The `EMBEDDED` comment in `build_super_bowl_snapshot.py` annotating
  each Super Bowl with its Roman numeral (including the
  "9/11-shifted XXXVI" and "first 2nd-Sunday-of-Feb LVI" notes) is a
  pleasure to read.
* The Wikidata-policy User-Agent string with `+https://...` URL
  follows the convention so politely it cheers up whoever's
  monitoring the SPARQL endpoint.
* The dev guide's ASCII diagram of the three-tier lookup is a
  generous gift.
* The decision to default `is_super_bowl_sunday(d)` to local-only is
  thoughtful; it tells the user "I've thought about your common case."

Things that *almost* delight but undersell:

* The 🏈/🎬 emoji-by-name composition pattern in `by_date.py` is
  delightful — but it's hidden in `examples/`. Move it to the README.
* `label_with_edition=True` is fun (Super Bowl LIX, 97th Academy
  Awards) but is shown only as a postscript. It deserves a dedicated
  block titled "Display strings."
* The dev guide's "network policy and failure modes" table is the
  kind of thing a senior engineer screencaps and pastes in a Slack
  thread. Promote one row of it to the README.

---

## 10. Specific README revision suggestions

A reorderable outline:

```
# special-days

(one-line tagline)
(one-line interop tagline — `holidays`-compatible)
(badges)

## What it is
- Three concrete use cases (3 lines, scannable)
- Status (one line)

## Install

## Quickstart — what's special about today?
(SpecialDays + holidays union, 6-line block)

## Two ways to use it
### Date-keyed (drop-in for `holidays`)
### Year-keyed (planner-style)

## Display strings
(label_with_edition example)

## Offline first, fresh when you need it
(short paragraph; failure modes; allow_network)

## Cache location

## Maintenance / contributing
(short, link to dev guide)

## License
```

That outline foregrounds the use case, brings the killer feature into
the first screen, and shrinks the "tests / maintenance" sections that
belong in `CONTRIBUTING.md`.

---

## 11. Summary scorecard

| Surface              | Verdict                                             |
|----------------------|-----------------------------------------------------|
| 5-second test        | Good — one-line "why" could move higher             |
| 60-second test       | Good — `holidays` interop should lead, not trail    |
| 5-minute test        | Mostly good — network failure mode underspecified   |
| Docstrings           | Excellent                                           |
| Dev guide            | Excellent content; wrong format/no link from README |
| Examples             | Short + illustrative; missing a bulk-preload one    |
| Error messages       | Above average; one could be sharper                 |
| PyPI metadata        | Good; minor URL/classifier/keyword additions        |
| Delight              | Many small wins, a few buried                       |

A first-time user *will* succeed with this package. With the
re-ordering proposed above, they will succeed and *enjoy* it.
