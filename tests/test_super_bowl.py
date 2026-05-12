"""Tests for the public super_bowl API."""

from datetime import date
from unittest import TestCase, mock

from special_days import super_bowl
from special_days._wikidata import WikidataUnavailable


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


class IsSuperBowlSundayTests(TestCase):
    def test_true_on_super_bowl_day(self):
        self.assertTrue(super_bowl.is_super_bowl_sunday(date(2025, 2, 9)))
        self.assertTrue(super_bowl.is_super_bowl_sunday(date(2024, 2, 11)))
        self.assertTrue(super_bowl.is_super_bowl_sunday(date(1967, 1, 15)))

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
    def test_raises_keyerror_when_year_unknown_and_no_network(self):
        with self.assertRaises(KeyError):
            super_bowl.date(2099, allow_network=False)

    @mock.patch("special_days.super_bowl._fetch_from_wikidata")
    def test_falls_back_to_network_when_year_missing(self, mock_fetch):
        mock_fetch.return_value = {2099: date(2099, 2, 14)}
        self.assertEqual(super_bowl.date(2099), date(2099, 2, 14))
        mock_fetch.assert_called_once()

    @mock.patch("special_days.super_bowl._fetch_from_wikidata")
    def test_does_not_call_network_when_year_in_snapshot(self, mock_fetch):
        super_bowl.date(2025)
        mock_fetch.assert_not_called()

    @mock.patch("special_days.super_bowl._fetch_from_wikidata")
    def test_raises_when_network_also_lacks_year(self, mock_fetch):
        mock_fetch.return_value = {}
        with self.assertRaises(KeyError):
            super_bowl.date(2099)


class RefreshTests(TestCase):
    @mock.patch("special_days.super_bowl._fetch_from_wikidata")
    def test_refresh_updates_known_dates(self, mock_fetch):
        mock_fetch.return_value = {
            2099: date(2099, 2, 14),
            2025: date(2025, 2, 9),
        }
        result = super_bowl.refresh()
        self.assertEqual(result[2099], date(2099, 2, 14))

    @mock.patch("special_days.super_bowl._fetch_from_wikidata")
    def test_refresh_propagates_network_errors(self, mock_fetch):
        mock_fetch.side_effect = WikidataUnavailable("network down")
        with self.assertRaises(WikidataUnavailable):
            super_bowl.refresh()


class SuperBowlClassTests(TestCase):
    """The holidays-compatible date-keyed class API."""

    def test_date_membership(self):
        sb = super_bowl.SuperBowl()
        self.assertIn(date(2025, 2, 9), sb)
        self.assertNotIn(date(2025, 2, 10), sb)

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

    def test_iteration_shows_only_loaded_dates(self):
        sb = super_bowl.SuperBowl()
        self.assertEqual(list(sb), [])  # nothing loaded yet
        _ = date(2025, 2, 9) in sb  # trigger load of year 2025
        self.assertEqual(list(sb), [date(2025, 2, 9)])

    def test_years_constructor_arg_eagerly_loads(self):
        sb = super_bowl.SuperBowl(years=[2024, 2025])
        self.assertEqual(set(sb), {date(2024, 2, 11), date(2025, 2, 9)})

    def test_years_constructor_accepts_single_int(self):
        sb = super_bowl.SuperBowl(years=2025)
        self.assertEqual(list(sb), [date(2025, 2, 9)])

    @mock.patch("special_days.super_bowl._fetch_from_wikidata")
    def test_unknown_year_does_not_repeat_network_calls(self, mock_fetch):
        mock_fetch.return_value = {}
        sb = super_bowl.SuperBowl()
        self.assertNotIn(date(2099, 2, 14), sb)
        self.assertNotIn(date(2099, 2, 14), sb)  # cached "not announced"
        self.assertEqual(mock_fetch.call_count, 1)

    @mock.patch("special_days.super_bowl._fetch_from_wikidata")
    def test_allow_network_false_skips_fetch(self, mock_fetch):
        sb = super_bowl.SuperBowl(allow_network=False)
        self.assertNotIn(date(2099, 2, 14), sb)
        mock_fetch.assert_not_called()

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


class SuperBowlClassRefreshTests(TestCase):
    @mock.patch("special_days.super_bowl._fetch_from_wikidata")
    def test_refresh_clears_loaded_state_then_repopulates_on_access(
        self, mock_fetch
    ):
        mock_fetch.return_value = {2025: date(2025, 2, 9)}
        sb = super_bowl.SuperBowl(years=2025)
        self.assertEqual(list(sb), [date(2025, 2, 9)])
        sb.refresh()
        self.assertEqual(list(sb), [])  # cleared
        _ = date(2025, 2, 9) in sb
        self.assertEqual(list(sb), [date(2025, 2, 9)])

    @mock.patch("special_days.super_bowl._fetch_from_wikidata")
    def test_refresh_raises_when_network_disabled(self, mock_fetch):
        sb = super_bowl.SuperBowl(allow_network=False, years=2025)
        with self.assertRaises(RuntimeError):
            sb.refresh()
        mock_fetch.assert_not_called()
        # State must be untouched after a refused refresh.
        self.assertEqual(list(sb), [date(2025, 2, 9)])
