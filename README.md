# special-days

[![tests](https://github.com/stringertheory/special-days/actions/workflows/ci.yml/badge.svg)](https://github.com/stringertheory/special-days/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/special-days.svg)](https://pypi.org/project/special-days/)

Lookup dates for special events, so far the Super Bowl Sunday and Oscars night. Compatible with the
[`holidays`](https://pypi.org/project/holidays/) package, so the same
`date in calendar` logic you can use for public holidays answers
"is today Super Bowl Sunday?" too.

Zero runtime dependencies. Data is
checked daily against Wikidata and, once manually reviewed and published, `pip install --upgrade` will pull the
refreshed known dates.

> **Status: Alpha.** Currently ships Super Bowl + Academy Awards
> (Oscars). The API probably won't change, but I might until
> the maintenance process has run for a while and I've
> learned if things need to change.

## Install

```bash
pip install special-days
```

## Quickstart

Answer "is this day special?" in the `holidays`-compatible way.

```python
from datetime import date
from special_days import SpecialDays

sd = SpecialDays()                       # all events the package ships
sd.get_list(date(2025, 2, 9))            # ['Super Bowl']
sd.get_list(date(2025, 3, 2))            # ['Academy Awards']
sd.get_list(date(2025, 5, 1))            # []
```

You can combine with the `holidays` package via `union(...)`:

```python
import holidays
from special_days import SpecialDays, union

combined = union(holidays.US(), SpecialDays())
combined.get_list(date(2025, 2, 9))      # ['Super Bowl']
combined.get_list(date(2025, 7, 4))      # ['Independence Day']
```

You can exclude some special days in most cases with something like this:

```python
EMOJI = {
    "Independence Day": "🎆",
    "Super Bowl":       "🏈",
}

def specials(d):
    return [(n, EMOJI[n]) for n in combined.get_list(d) if n in EMOJI]

specials(date(2025, 2, 9))               # [('Super Bowl', '🏈')]
specials(date(2025, 7, 4))               # [('Independence Day', '🎆')]
specials(date(2025, 12, 25))             # []
```

A more full version is in [`examples/by_date.py`](examples/by_date.py).

## Two ways to use it

### Date-keyed (drop-in for `holidays`)

A `dict`-like subclass populated from the included data snapshot.

```python
from datetime import date
from special_days import SuperBowl

sb = SuperBowl()                         # every known Super Bowl date
date(2025, 2, 9) in sb                   # True
sb[date(2025, 2, 9)]                     # 'Super Bowl'
sb.get_list(date(2025, 2, 9))            # ['Super Bowl']
len(sb)                                  # one entry per game, grows each year

# Filter to a subset of years.
SuperBowl(years=[1967, 2024, 2025])
SuperBowl(years=range(2020, 2030))
```

`datetime.datetime` values are normalized to `date` automatically, so
mixing the two in a lookup just works.

### Year-keyed (planner-style)

```python
from datetime import date
from special_days import super_bowl

super_bowl.date(2025)                    # datetime.date(2025, 2, 9)
super_bowl.is_super_bowl_sunday(date(2025, 2, 9))   # True
super_bowl.all_known()                   # {1967: date(1967, 1, 15), ..., 2027: date(2027, 2, 14)}
```

## Display strings

By default the dict value is the constant event name (`"Super Bowl"`,
`"Academy Awards"`). Pass `label_with_edition=True` for
edition-numbered display strings:

```python
SuperBowl(label_with_edition=True)[date(2025, 2, 9)]     # 'Super Bowl LIX'
Oscars(label_with_edition=True)[date(2025, 3, 2)]        # '97th Academy Awards'
```

Super Bowl 50 (2016) uses the Arabic numeral, matching official NFL
branding; every other edition uses Roman. The Academy Awards labeller
handles 1930's two ceremonies (the 2nd in April, the 3rd in November)
and the subsequent resync at the 6th ceremony in 1934.

## Two ceremonies in one year

Most series have at most one installment per year, but not all. 1930
hosted two Academy Awards (the 2nd and 3rd):

```python
from special_days import oscars

oscars.date(1930)                        # datetime.date(1930, 4, 3)  -- first only
oscars.dates(1930)                       # [date(1930, 4, 3), date(1930, 11, 5)]
```

`SpecialDays`/`Oscars` dicts contain *both* dates and label them
distinctly when `label_with_edition=True`.

## Recipes

### Next upcoming event from today

`is_super_bowl_sunday` over a date range, or just iterate `dates()` /
`all_known()`:

```python
from datetime import date, timedelta
from special_days import super_bowl

today = date.today()
upcoming = next(
    d for d in (today + timedelta(days=i) for i in range(365 * 2))
    if super_bowl.is_super_bowl_sunday(d)
)
```

### All special days in a date range

```python
from datetime import date, timedelta
from special_days import SpecialDays

sd = SpecialDays()
start, end = date(2025, 1, 1), date(2025, 12, 31)
days = [d for d in (start + timedelta(days=i)
                    for i in range((end - start).days + 1))
        if d in sd]
# [date(2025, 2, 9), date(2025, 3, 2)]
```

### Just one event, not all of them

`SpecialDays(events=[...])` accepts string names, classes, or
already-built instances:

```python
from special_days import SpecialDays, SuperBowl

SpecialDays(events=["super_bowl"])      # by registered name
SpecialDays(events=[SuperBowl])         # by class
SpecialDays(events=[SuperBowl(years=[2024, 2025])])   # pre-filtered instance
```

## Data freshness

The shipped snapshot covers every event in Wikidata at
release time — every past game and every officially-announced future
game. A daily job rebuilds the snapshot from Wikidata; if anything
changed, it opens a PR. Once manually reviewed and merged, a new patch release will be created on
PyPI. Run `pip install --upgrade special-days` to pull the latest.

For maintainers and curious users, the full pipeline is documented in
[`docs/how_it_works.md`](docs/how_it_works.md).

## Errors

* `super_bowl.date(year)` raises `KeyError` if the year is not in the
  shipped snapshot. Upgrade the package to pick up newly-announced
  dates.
* Non-`int` `year` arguments raise `TypeError` immediately.
* `SpecialDays(events=[...])` raises `ValueError` for unknown event
  strings, listing the valid ones.

## License

MIT
