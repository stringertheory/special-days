"""Which future Super Bowls have been announced?

Walks forward year by year, asking the package for each date. Unknown
years raise ``KeyError`` -- meaning "not in the shipped snapshot".
Upgrade the package (``pip install --upgrade special-days``) to pick
up newly-announced dates.
"""

from datetime import date

from special_days import super_bowl


def main():
    today = date.today()
    print(f"Today: {today.isoformat()}\n")

    for year in range(today.year, today.year + 10):
        try:
            d = super_bowl.date(year)
        except KeyError:
            print(f"{year}: not announced")
            continue
        when = "past" if d < today else "upcoming"
        print(f"{year}: {d.isoformat()}  ({when})")


if __name__ == "__main__":
    main()
