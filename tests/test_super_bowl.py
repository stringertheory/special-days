"""Tests for the public super_bowl API."""

from datetime import date, datetime
from unittest import TestCase

from special_days import super_bowl


class KnownDatesFromSnapshotTests(TestCase):
    """The shipped snapshot must answer common queries offline."""

    def test_returns_super_bowl_i(self):
        self.assertEqual(super_bowl.date(1967), date(1967, 1, 15))

    def test_returns_super_bowl_50(self):
        self.assertEqual(super_bowl.date(2016), date(2016, 2, 7))

    def test_returns_recent_super_bowl(self):
        self.assertEqual(super_bowl.date(2025), date(2025, 2, 9))

    def test_returns_announced_future_super_bowl(self):
        self.assertEqual(super_bowl.date(2026), date(2026, 2, 8))


class DatesFunctionTests(TestCase):
    def test_dates_returns_single_element_list(self):
        self.assertEqual(super_bowl.dates(2025), [date(2025, 2, 9)])

    def test_dates_unknown_year_returns_empty_list(self):
        self.assertEqual(super_bowl.dates(1900), [])


class IsSuperBowlSundayTests(TestCase):
    def test_true_on_super_bowl_day(self):
        self.assertTrue(super_bowl.is_super_bowl_sunday(date(2025, 2, 9)))
        self.assertTrue(super_bowl.is_super_bowl_sunday(date(2024, 2, 11)))
        self.assertTrue(super_bowl.is_super_bowl_sunday(date(1967, 1, 15)))

    def test_true_on_datetime_normalized_to_date(self):
        self.assertTrue(super_bowl.is_super_bowl_sunday(datetime(2025, 2, 9)))
        self.assertTrue(
            super_bowl.is_super_bowl_sunday(datetime(2025, 2, 9, 18, 30))
        )

    def test_false_when_off_by_one_day(self):
        self.assertFalse(super_bowl.is_super_bowl_sunday(date(2025, 2, 10)))
        self.assertFalse(super_bowl.is_super_bowl_sunday(date(2025, 2, 8)))

    def test_false_on_unrelated_date(self):
        self.assertFalse(super_bowl.is_super_bowl_sunday(date(2025, 7, 4)))


class AllKnownTests(TestCase):
    def test_returns_dict_keyed_by_year(self):
        known = super_bowl.all_known()
        self.assertIsInstance(known, dict)
        self.assertEqual(known[2025], date(2025, 2, 9))

    def test_returned_dict_is_a_copy(self):
        a = super_bowl.all_known()
        a[1900] = date(1900, 1, 1)
        b = super_bowl.all_known()
        self.assertNotIn(1900, b)


class UnknownYearTests(TestCase):
    def test_raises_keyerror_when_year_unknown(self):
        with self.assertRaises(KeyError):
            super_bowl.date(2099)

    def test_rejects_non_int_year(self):
        with self.assertRaises(TypeError):
            super_bowl.date("2025")  # type: ignore[arg-type]


class SuperBowlClassTests(TestCase):
    """The holidays-compatible date-keyed class API."""

    def test_date_membership(self):
        sb = super_bowl.SuperBowl()
        self.assertIn(date(2025, 2, 9), sb)
        self.assertNotIn(date(2025, 2, 10), sb)

    def test_datetime_membership_is_normalized_to_date(self):
        sb = super_bowl.SuperBowl()
        self.assertIn(datetime(2025, 2, 9), sb)
        self.assertIn(datetime(2025, 2, 9, 12, 0, 0), sb)

    def test_lookup_returns_constant_label_by_default(self):
        sb = super_bowl.SuperBowl()
        self.assertEqual(sb[date(2025, 2, 9)], "Super Bowl")
        self.assertEqual(sb[date(2024, 2, 11)], "Super Bowl")

    def test_get_returns_default_for_unknown_date(self):
        sb = super_bowl.SuperBowl()
        self.assertIsNone(sb.get(date(2025, 2, 10)))
        self.assertEqual(sb.get(date(2025, 2, 10), "nope"), "nope")

    def test_get_list_returns_label_for_event_date(self):
        sb = super_bowl.SuperBowl()
        self.assertEqual(sb.get_list(date(2025, 2, 9)), ["Super Bowl"])

    def test_get_list_empty_for_non_event_date(self):
        sb = super_bowl.SuperBowl()
        self.assertEqual(sb.get_list(date(2025, 7, 4)), [])

    def test_iteration_yields_every_snapshot_date(self):
        # SuperBowl() with no `years=` filter loads every date in the
        # shipped snapshot.
        sb = super_bowl.SuperBowl()
        self.assertGreater(len(sb), 50)
        self.assertIn(date(1967, 1, 15), sb)
        self.assertIn(date(2025, 2, 9), sb)

    def test_years_filter_restricts_to_listed_years(self):
        sb = super_bowl.SuperBowl(years=[2024, 2025])
        self.assertEqual(set(sb), {date(2024, 2, 11), date(2025, 2, 9)})

    def test_years_filter_accepts_single_int(self):
        sb = super_bowl.SuperBowl(years=2025)
        self.assertEqual(list(sb), [date(2025, 2, 9)])

    def test_years_filter_rejects_non_int(self):
        with self.assertRaises(TypeError):
            super_bowl.SuperBowl(years=["2025"])  # type: ignore[list-item]

    def test_label_with_edition_emits_roman(self):
        sb = super_bowl.SuperBowl(label_with_edition=True, years=2025)
        self.assertEqual(sb[date(2025, 2, 9)], "Super Bowl LIX")

    def test_label_with_edition_handles_super_bowl_50(self):
        # SB 50 (2016) was officially marketed with the Arabic numeral.
        sb = super_bowl.SuperBowl(label_with_edition=True, years=2016)
        self.assertEqual(sb[date(2016, 2, 7)], "Super Bowl 50")

    def test_label_with_edition_roman_corners(self):
        # Spot-check a few editions to catch off-by-one bugs in _roman.
        sb = super_bowl.SuperBowl(label_with_edition=True)
        self.assertEqual(sb[date(1967, 1, 15)], "Super Bowl I")  # 1
        self.assertEqual(sb[date(1970, 1, 11)], "Super Bowl IV")  # 4
        self.assertEqual(sb[date(2024, 2, 11)], "Super Bowl LVIII")  # 58


class RomanNumeralEdgeCaseTests(TestCase):
    """``roman`` must use standard subtractive notation through 3999."""

    def test_subtractive_notation_used_above_399(self):
        from special_days._numerals import roman

        self.assertEqual(roman(400), "CD")
        self.assertEqual(roman(500), "D")
        self.assertEqual(roman(900), "CM")
        self.assertEqual(roman(1000), "M")
        self.assertEqual(roman(3999), "MMMCMXCIX")
