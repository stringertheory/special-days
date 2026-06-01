"""Opt-in tests that hit the real Wikidata SPARQL endpoint.

Skipped by default. Enable with:

    SPECIAL_DAYS_LIVE_TESTS=1 python -m unittest tests.test_live_wikidata

These verify that the SPARQL query still works against the live
Wikidata service. If Wikidata reshapes its data (rare, but possible
over 20 years), these tests will fail loudly and tell you to update
the query.
"""

import os
import unittest
from datetime import date

from special_days import oscars, super_bowl
from special_days.wikidata import fetch_event_dates

LIVE = os.environ.get("SPECIAL_DAYS_LIVE_TESTS") == "1"


@unittest.skipUnless(LIVE, "Set SPECIAL_DAYS_LIVE_TESTS=1 to enable.")
class LiveSuperBowlTests(unittest.TestCase):
    # Fetch once per run and share across the assertions below. The
    # public Wikidata endpoint is slow and rate-limited; one query per
    # test method would multiply both the flakiness and the load.
    @classmethod
    def setUpClass(cls):
        cls.result = fetch_event_dates(super_bowl.EVENT.wikidata_qid)

    def test_super_bowl_query_returns_known_dates(self):
        # Historical facts -- if Wikidata disagrees with them, either
        # Wikidata is wrong or the query is matching wrong entities.
        self.assertEqual(self.result.get(1967), [date(1967, 1, 15)])
        self.assertEqual(self.result.get(2016), [date(2016, 2, 7)])
        self.assertEqual(self.result.get(2025), [date(2025, 2, 9)])

    def test_super_bowl_query_returns_reasonable_count(self):
        # There have been ~60 Super Bowls. If the query returns
        # nothing or 1000s, something's wrong with it.
        self.assertGreater(len(self.result), 50)
        self.assertLess(len(self.result), 200)

    def test_all_returned_dates_are_sundays(self):
        """Every Super Bowl has been played on a Sunday. A non-Sunday
        in the result almost always means the query matched a Wikidata
        date with imprecise precision (e.g. 'February 2029' stored as
        2029-02-01) and didn't filter it out.
        """
        non_sundays = {
            y: ds
            for y, ds in self.result.items()
            if any(d.weekday() != 6 for d in ds)
        }
        self.assertEqual(non_sundays, {})


@unittest.skipUnless(LIVE, "Set SPECIAL_DAYS_LIVE_TESTS=1 to enable.")
class LiveOscarsTests(unittest.TestCase):
    # See LiveSuperBowlTests: one shared fetch per run, not per method.
    @classmethod
    def setUpClass(cls):
        cls.result = fetch_event_dates(oscars.EVENT.wikidata_qid)

    def test_oscars_query_returns_known_dates(self):
        # Modern, easily-verifiable ceremony dates.
        self.assertEqual(self.result.get(1929), [date(1929, 5, 16)])  # 1st
        self.assertEqual(self.result.get(2024), [date(2024, 3, 10)])  # 96th
        self.assertEqual(self.result.get(2025), [date(2025, 3, 2)])  # 97th

    def test_oscars_query_has_no_1928_ceremony(self):
        """Q109886 (1st Academy Awards) once carried a spurious
        1928-05-16 P585 claim that the package filtered out at the
        package level. The bad claim was eventually deleted upstream.
        This test stays as a regression guard: if it fails, someone
        re-introduced a 1928 ceremony to Wikidata's Academy Awards
        graph.
        """
        self.assertNotIn(1928, self.result)

    def test_oscars_query_includes_both_1930_ceremonies(self):
        """1930 had two ceremonies: the 2nd on April 3 and the 3rd on
        November 5. Both should come back from the live query.
        """
        self.assertIn(1930, self.result)
        self.assertIn(date(1930, 4, 3), self.result[1930])
        self.assertIn(date(1930, 11, 5), self.result[1930])

    def test_oscars_query_returns_reasonable_count(self):
        total = sum(len(ds) for ds in self.result.values())
        # 97+ ceremonies since 1929. If the query returns nothing or
        # 1000s, something's wrong with it.
        self.assertGreater(total, 80)
        self.assertLess(total, 200)
