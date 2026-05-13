"""Tests for the public oscars API."""

from datetime import date, datetime
from unittest import TestCase

from special_days import oscars


class KnownDatesFromSnapshotTests(TestCase):
    """The shipped snapshot must answer common queries offline."""

    def test_returns_first_ceremony(self):
        # 1st Academy Awards: May 16, 1929.
        self.assertEqual(oscars.date(1929), date(1929, 5, 16))

    def test_returns_recent_ceremony(self):
        # 97th Academy Awards: March 2, 2025.
        self.assertEqual(oscars.date(2025), date(2025, 3, 2))

    def test_returns_announced_future_ceremony(self):
        # 98th Academy Awards: March 15, 2026.
        self.assertEqual(oscars.date(2026), date(2026, 3, 15))


class TwoCeremoniesInOneYearTests(TestCase):
    """1930 had two ceremonies: the 2nd in April, the 3rd in November.

    ``date(year)`` returns the earliest; ``dates(year)`` returns both.
    """

    def test_date_returns_earliest_in_year(self):
        self.assertEqual(oscars.date(1930), date(1930, 4, 3))

    def test_dates_returns_both(self):
        self.assertEqual(
            oscars.dates(1930),
            [date(1930, 4, 3), date(1930, 11, 5)],
        )

    def test_is_oscars_night_recognizes_both(self):
        self.assertTrue(oscars.is_oscars_night(date(1930, 4, 3)))
        self.assertTrue(oscars.is_oscars_night(date(1930, 11, 5)))


class IsOscarsNightTests(TestCase):
    def test_true_on_oscars_night(self):
        self.assertTrue(oscars.is_oscars_night(date(2025, 3, 2)))
        self.assertTrue(oscars.is_oscars_night(date(2024, 3, 10)))

    def test_false_when_off_by_one_day(self):
        self.assertFalse(oscars.is_oscars_night(date(2025, 3, 3)))
        self.assertFalse(oscars.is_oscars_night(date(2025, 3, 1)))

    def test_false_on_unrelated_date(self):
        self.assertFalse(oscars.is_oscars_night(date(2025, 7, 4)))


class AllKnownTests(TestCase):
    def test_returns_dict_keyed_by_year(self):
        known = oscars.all_known()
        self.assertIsInstance(known, dict)
        self.assertEqual(known[2025], date(2025, 3, 2))

    def test_returned_dict_is_a_copy(self):
        a = oscars.all_known()
        a[1800] = date(1800, 1, 1)
        b = oscars.all_known()
        self.assertNotIn(1800, b)


class UnknownYearTests(TestCase):
    def test_raises_keyerror_when_year_unknown(self):
        with self.assertRaises(KeyError):
            oscars.date(2099)

    def test_rejects_non_int_year(self):
        with self.assertRaises(TypeError):
            oscars.date("2025")  # type: ignore[arg-type]


class OscarsClassTests(TestCase):
    """The holidays-compatible date-keyed class API."""

    def test_date_membership(self):
        o = oscars.Oscars()
        self.assertIn(date(2025, 3, 2), o)
        self.assertNotIn(date(2025, 3, 3), o)

    def test_datetime_membership_is_normalized(self):
        o = oscars.Oscars()
        self.assertIn(datetime(2025, 3, 2), o)

    def test_lookup_returns_constant_label_by_default(self):
        o = oscars.Oscars()
        self.assertEqual(o[date(2025, 3, 2)], "Academy Awards")
        self.assertEqual(o[date(2024, 3, 10)], "Academy Awards")

    def test_get_list_returns_label_for_event_date(self):
        o = oscars.Oscars()
        self.assertEqual(o.get_list(date(2025, 3, 2)), ["Academy Awards"])

    def test_get_list_empty_for_non_event_date(self):
        o = oscars.Oscars()
        self.assertEqual(o.get_list(date(2025, 7, 4)), [])

    def test_years_constructor_arg_eagerly_loads(self):
        o = oscars.Oscars(years=[2024, 2025])
        self.assertEqual(set(o), {date(2024, 3, 10), date(2025, 3, 2)})

    def test_years_constructor_loads_all_dates_in_year(self):
        # 1930 has two ceremonies; both should be in the dict.
        o = oscars.Oscars(years=1930)
        self.assertEqual(set(o), {date(1930, 4, 3), date(1930, 11, 5)})

    def test_label_with_edition_emits_ordinal(self):
        o = oscars.Oscars(label_with_edition=True, years=2025)
        self.assertEqual(o[date(2025, 3, 2)], "97th Academy Awards")

    def test_label_with_edition_first_ceremony(self):
        o = oscars.Oscars(label_with_edition=True, years=1929)
        self.assertEqual(o[date(1929, 5, 16)], "1st Academy Awards")

    def test_label_with_edition_distinguishes_two_in_1930(self):
        """The 2nd (April) and 3rd (November) Academy Awards both
        happened in 1930 and must get distinct edition labels."""
        o = oscars.Oscars(label_with_edition=True, years=1930)
        self.assertEqual(o[date(1930, 4, 3)], "2nd Academy Awards")
        self.assertEqual(o[date(1930, 11, 5)], "3rd Academy Awards")

    def test_label_with_edition_post_collision_resync(self):
        """The 4th, 5th, and 6th ceremonies fall in 1931, 1932, 1934
        respectively (no ceremony in 1933). A naive year-1928 offset
        would mislabel 1931 as the 3rd and 1932 as the 4th."""
        o = oscars.Oscars(label_with_edition=True)
        self.assertEqual(o[date(1931, 11, 10)], "4th Academy Awards")
        self.assertEqual(o[date(1932, 11, 18)], "5th Academy Awards")
        self.assertEqual(o[date(1934, 3, 16)], "6th Academy Awards")

    def test_ordinal_corners(self):
        # Spot-check via the public label path for off-by-one bugs.
        o = oscars.Oscars(label_with_edition=True)
        # 21st (year 1949) -> "21st" not "21nd"
        self.assertEqual(o[date(1949, 3, 24)], "21st Academy Awards")
        # 22nd (1950) -> "22nd"
        self.assertEqual(o[date(1950, 3, 23)], "22nd Academy Awards")
        # 23rd (1951) -> "23rd"
        self.assertEqual(o[date(1951, 3, 29)], "23rd Academy Awards")
