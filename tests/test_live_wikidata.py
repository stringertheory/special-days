"""Opt-in tests that hit the real Wikidata SPARQL endpoint.

Skipped by default. Enable with:

    SPECIAL_DAYS_LIVE_TESTS=1 python -m unittest tests.test_live_wikidata

These verify that our SPARQL query still works against the live Wikidata
service. If Wikidata reshapes its data (rare, but possible over 20 years),
these tests will fail loudly and tell you to update the query.
"""

import os
import unittest
from datetime import date

from special_days._wikidata import fetch_super_bowl_dates

LIVE = os.environ.get("SPECIAL_DAYS_LIVE_TESTS") == "1"


@unittest.skipUnless(LIVE, "Set SPECIAL_DAYS_LIVE_TESTS=1 to enable.")
class LiveWikidataTests(unittest.TestCase):
    def test_super_bowl_query_returns_known_dates(self):
        result = fetch_super_bowl_dates()
        # These are historical facts — if Wikidata disagrees with them,
        # either Wikidata is wrong or our query is matching wrong entities.
        self.assertEqual(result.get(1967), date(1967, 1, 15))
        self.assertEqual(result.get(2016), date(2016, 2, 7))
        self.assertEqual(result.get(2025), date(2025, 2, 9))

    def test_super_bowl_query_returns_reasonable_count(self):
        result = fetch_super_bowl_dates()
        # There have been ~60 Super Bowls. If we get nothing or 1000s,
        # something's wrong with the query.
        self.assertGreater(len(result), 50)
        self.assertLess(len(result), 200)

    def test_all_returned_dates_are_sundays(self):
        """Every Super Bowl has been played on a Sunday. A non-Sunday
        in our results almost always means we matched a Wikidata date
        with imprecise precision (e.g. 'February 2029' stored as
        2029-02-01) and didn't filter it out.
        """
        result = fetch_super_bowl_dates()
        # weekday(): Monday is 0, Sunday is 6.
        non_sundays = {y: d for y, d in result.items() if d.weekday() != 6}
        self.assertEqual(non_sundays, {})
