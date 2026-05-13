# special-days

[![tests](https://github.com/stringertheory/special-days/actions/workflows/ci.yml/badge.svg)](https://github.com/stringertheory/special-days/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/special-days.svg)](https://pypi.org/project/special-days/)

Lookup dates for special events — Super Bowl Sunday, Oscars night,
World Series Game 7, NCAA championship. Drop-in compatible with the
[`holidays`](https://pypi.org/project/holidays/) package, so the same
`date in calendar` logic you already use for public holidays answers
"is today Super Bowl Sunday?" too.

Zero runtime dependencies. All lookups are local; no network calls
are made at runtime. Data is refreshed in CI from Wikidata; `pip
install --upgrade` pulls fresh dates.

> **Status: Beta.** Currently ships Super Bowl + Academy Awards
> (Oscars). The API is settling; behavior-changing edits will land on
> minor-version bumps until 1.0.

## Install

```bash
pip install special-days
```

## Quickstart — "what's special about today?"

The most common use: ask "is this date significant?" in the
`holidays`-compatible way.

```python
from datetime import date
from special_days import SpecialDays

sd = SpecialDays()                       # all events the package ships
sd.get_list(date(2025, 2, 9))            # ['Super Bowl']
sd.get_list(date(2025, 3, 2))            # ['Academy Awards']
sd.get_list(date(2025, 5, 1))            # []
```

Compose with the `holidays` package via `union(...)`, preserving
laziness on both sides:

```python
import holidays
from special_days import SpecialDays, union

combined = union(holidays.US(), SpecialDays())
combined.get_list(date(2025, 2, 9))      # ['Super Bowl']
combined.get_list(date(2025, 7, 4))      # ['Independence Day']
```

A complete "emoji per special day" demo lives in
[`examples/by_date.py`](examples/by_date.py).

## Two ways to use it

### Date-keyed (drop-in for `holidays`)

A dict-like class keyed by `datetime.date`, lazy on construction —
only years you actually query get loaded.

```python
from datetime import date
from special_days import SuperBowl

sb = SuperBowl()
date(2025, 2, 9) in sb                   # True
sb[date(2025, 2, 9)]                     # 'Super Bowl'
sb.get_list(date(2025, 2, 9))            # ['Super Bowl']

# Eager mode, like holidays.US(years=2025).
SuperBowl(years=[1967, 2024, 2025])

# Or preload a whole range.
SuperBowl(years=range(1967, 2027))
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

Pick whichever shape fits the question.

## Display strings

By default the dict value is the constant event name (`"Super Bowl"`,
`"Academy Awards"`). Pass `label_with_edition=True` for
edition-numbered display strings:

```python
SuperBowl(label_with_edition=True)[date(2025, 2, 9)]    # 'Super Bowl LIX'
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

## Data freshness

The shipped snapshot covers every event known to the maintainers at
release time — every past game and every officially-announced future
game. A daily CI job rebuilds the snapshot from Wikidata; if anything
changed, it opens a PR. Once merged, a new patch release ships to
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
