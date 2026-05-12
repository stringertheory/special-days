# special-days

Lookup dates for events that cause unusual attendance patterns at venues:
Super Bowl Sunday, Oscars night, World Series Game 7, NCAA championship,
etc. Data is sourced from [Wikidata](https://www.wikidata.org), so it
doesn't go stale.

Zero runtime dependencies — only the Python standard library.

## Status

Alpha. Currently supports: Super Bowl, Academy Awards (Oscars). More events to come.

## Install

```bash
pip install special-days
```

## Use

Two APIs over the same data. Pick whichever fits your question.

### Year-keyed (planner-style)

```python
from datetime import date
from special_days import super_bowl

super_bowl.date(2025)
# datetime.date(2025, 2, 9)

super_bowl.is_super_bowl_sunday(date(2025, 2, 9))
# True

super_bowl.all_known()
# {1967: date(1967, 1, 15), ..., 2026: date(2026, 2, 8)}
```

### Date-keyed (`holidays`-compatible)

A dict-like class keyed by `datetime.date`, lazy on construction — only
years you actually query get loaded.

```python
from datetime import date
from special_days import SuperBowl, SpecialDays, union

sb = SuperBowl()
date(2025, 2, 9) in sb           # True
sb[date(2025, 2, 9)]             # 'Super Bowl'
sb.get_list(date(2025, 2, 9))    # ['Super Bowl']

# eager mode, like holidays.US(years=2025)
SuperBowl(years=[2024, 2025])

# edition-numbered labels for display strings
SuperBowl(label_with_edition=True)[date(2025, 2, 9)]    # 'Super Bowl LIX'
```

Compose with the [`holidays`](https://pypi.org/project/holidays/) package
via `union(...)`, preserving laziness on both sides:

```python
import holidays
from special_days import SpecialDays, union

combined = union(holidays.US(), SpecialDays())   # all known events
combined.get_list(date(2025, 2, 9))    # ['Super Bowl']
combined.get_list(date(2025, 3, 2))    # ['Academy Awards']
combined.get_list(date(2025, 7, 4))    # ['Independence Day']
```

`SpecialDays(events=...)` accepts registered string names
(`"super_bowl"`, `"oscars"`), event classes (`SuperBowl`, `Oscars`),
or pre-built instances. With no argument it includes everything the
package ships.

### Far-future years

A snapshot through Super Bowl LX (Feb 8, 2026) ships with the package, so
lookups for known years work offline. Asking for an unknown year
transparently refreshes from Wikidata:

```python
super_bowl.date(2035)   # hits Wikidata, caches the result
```

Disable the network fallback explicitly if you need it:

```python
super_bowl.date(2035, allow_network=False)   # raises KeyError
```

Force a refresh:

```python
super_bowl.refresh()   # re-fetch everything, update local cache
```

## Why Wikidata?

- **Structured.** Each Super Bowl has a stable Q-ID with a "point in
  time" property. We query that property directly — no HTML scraping,
  no infobox parsing.
- **Long-lived.** Wikidata has been stable since 2012 and is increasingly
  the upstream source for Wikipedia infoboxes.
- **Public, no auth.** No API keys, no signup, generous rate limits for
  conservative use like ours.

The package ships an offline snapshot so first use doesn't require
network, and degrades gracefully when Wikidata is unreachable.

## Cache

Refreshed data is cached at
`$XDG_CACHE_HOME/special-days/` (or `~/.cache/special-days/` on most
systems). Safe to delete; it will be repopulated.

## Tests

```bash
make venv && make install      # one-time setup
make test                      # unit tests (mocked HTTP) — fast, always run
make test-live                 # opt-in: hits the real Wikidata SPARQL endpoint
```

The live tests exist precisely to catch the case where Wikidata reshapes
its data and our SPARQL query stops returning the right items. If they
fail, update `EVENT_DATES_QUERY` in `src/special_days/_wikidata.py` and
cut a new release.

## Maintenance

To regenerate every shipped snapshot from current Wikidata data:

```bash
make snapshots-live
```

`make snapshots` (no `-live`) writes embedded hand-curated lists where
they exist — use this if Wikidata is wrong about a specific date and
you want to ship a correction. Per-event targets:
`make snapshot-super-bowl`, `make snapshot-super-bowl-live`,
`make snapshot-oscars`, `make snapshot-oscars-live`.

## License

MIT
