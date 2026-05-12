"""Tests for the public oscars API."""

from datetime import date
from unittest import TestCase, mock

from special_days import oscars
from special_days._wikidata import WikidataUnavailable


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
    def test_raises_keyerror_when_year_unknown_and_no_network(self):
        with self.assertRaises(KeyError):
            oscars.date(2099, allow_network=False)

    @mock.patch("special_days.oscars._fetch_from_wikidata")
    def test_falls_back_to_network_when_year_missing(self, mock_fetch):
        mock_fetch.return_value = {2099: date(2099, 3, 5)}
        self.assertEqual(oscars.date(2099), date(2099, 3, 5))
        mock_fetch.assert_called_once()

    @mock.patch("special_days.oscars._fetch_from_wikidata")
    def test_does_not_call_network_when_year_in_snapshot(self, mock_fetch):
        oscars.date(2025)
        mock_fetch.assert_not_called()

    @mock.patch("special_days.oscars._fetch_from_wikidata")
    def test_raises_when_network_also_lacks_year(self, mock_fetch):
        mock_fetch.return_value = {}
        with self.assertRaises(KeyError):
            oscars.date(2099)


class RefreshTests(TestCase):
    @mock.patch("special_days.oscars._fetch_from_wikidata")
    def test_refresh_updates_known_dates(self, mock_fetch):
        mock_fetch.return_value = {
            2099: date(2099, 3, 5),
            2025: date(2025, 3, 2),
        }
        result = oscars.refresh()
        self.assertEqual(result[2099], date(2099, 3, 5))

    @mock.patch("special_days.oscars._fetch_from_wikidata")
    def test_refresh_propagates_network_errors(self, mock_fetch):
        mock_fetch.side_effect = WikidataUnavailable("network down")
        with self.assertRaises(WikidataUnavailable):
            oscars.refresh()


class OscarsClassTests(TestCase):
    """The holidays-compatible date-keyed class API."""

    def test_date_membership(self):
        o = oscars.Oscars()
        self.assertIn(date(2025, 3, 2), o)
        self.assertNotIn(date(2025, 3, 3), o)

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

    def test_label_with_edition_emits_ordinal(self):
        o = oscars.Oscars(label_with_edition=True, years=2025)
        self.assertEqual(o[date(2025, 3, 2)], "97th Academy Awards")

    def test_label_with_edition_first_ceremony(self):
        o = oscars.Oscars(label_with_edition=True, years=1929)
        self.assertEqual(o[date(1929, 5, 16)], "1st Academy Awards")

    def test_ordinal_corners(self):
        # Spot-check via the public label path for off-by-one bugs.
        o = oscars.Oscars(label_with_edition=True)
        # 2nd Academy Awards: 1930 (year - 1928 = 2).
        self.assertEqual(o[date(1930, 4, 3)], "2nd Academy Awards")
        # 3rd is not in our snapshot due to two-in-1930 issue; skip.
        # 21st (year 1949) -> "21st" not "21nd"
        self.assertEqual(o[date(1949, 3, 24)], "21st Academy Awards")
        # 22nd (1950) -> "22nd"
        self.assertEqual(o[date(1950, 3, 23)], "22nd Academy Awards")
        # 23rd (1951) -> "23rd"
        self.assertEqual(o[date(1951, 3, 29)], "23rd Academy Awards")

    @mock.patch("special_days.oscars._fetch_from_wikidata")
    def test_allow_network_false_skips_fetch(self, mock_fetch):
        o = oscars.Oscars(allow_network=False)
        self.assertNotIn(date(2099, 3, 5), o)
        mock_fetch.assert_not_called()

    @mock.patch("special_days.oscars._fetch_from_wikidata")
    def test_refresh_raises_when_network_disabled(self, mock_fetch):
        o = oscars.Oscars(allow_network=False, years=2025)
        with self.assertRaises(RuntimeError):
            o.refresh()
        mock_fetch.assert_not_called()
