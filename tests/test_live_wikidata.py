"""Opt-in tests that hit the real Wikidata SPARQL endpoint.

Skipped by default. Enable with:

    SPECIAL_DAYS_LIVE_TESTS=1 python -m unittest tests.test_live_wikidata

These verify that our SPARQL query still works against the live
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
    def test_super_bowl_query_returns_known_dates(self):
        result = fetch_event_dates(super_bowl.EVENT.wikidata_qid)
        # Historical facts -- if Wikidata disagrees with them, either
        # Wikidata is wrong or our query is matching wrong entities.
        self.assertEqual(result.get(1967), [date(1967, 1, 15)])
        self.assertEqual(result.get(2016), [date(2016, 2, 7)])
        self.assertEqual(result.get(2025), [date(2025, 2, 9)])

    def test_super_bowl_query_returns_reasonable_count(self):
        result = fetch_event_dates(super_bowl.EVENT.wikidata_qid)
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
        result = fetch_event_dates(super_bowl.EVENT.wikidata_qid)
        non_sundays = {
            y: ds
            for y, ds in result.items()
            if any(d.weekday() != 6 for d in ds)
        }
        self.assertEqual(non_sundays, {})


@unittest.skipUnless(LIVE, "Set SPECIAL_DAYS_LIVE_TESTS=1 to enable.")
class LiveOscarsTests(unittest.TestCase):
    def test_oscars_query_returns_known_dates(self):
        result = fetch_event_dates(oscars.EVENT.wikidata_qid)
        # Modern, easily-verifiable ceremony dates.
        self.assertEqual(result.get(1929), [date(1929, 5, 16)])  # 1st
        self.assertEqual(result.get(2024), [date(2024, 3, 10)])  # 96th
        self.assertEqual(result.get(2025), [date(2025, 3, 2)])  # 97th

    def test_oscars_query_has_no_1928_ceremony(self):
        """Q109886 (1st Academy Awards) once carried a spurious
        1928-05-16 P585 claim that we filtered out at the package
        level. The bad claim was eventually deleted upstream. This
        test stays as a regression guard: if it fails, someone
        re-introduced a 1928 ceremony to Wikidata's Academy Awards
        graph.
        """
        result = fetch_event_dates(oscars.EVENT.wikidata_qid)
        self.assertNotIn(1928, result)

    def test_oscars_query_includes_both_1930_ceremonies(self):
        """1930 had two ceremonies: the 2nd on April 3 and the 3rd on
        November 5. Both should come back from the live query.
        """
        result = fetch_event_dates(oscars.EVENT.wikidata_qid)
        self.assertIn(1930, result)
        self.assertIn(date(1930, 4, 3), result[1930])
        self.assertIn(date(1930, 11, 5), result[1930])

    def test_oscars_query_returns_reasonable_count(self):
        result = fetch_event_dates(oscars.EVENT.wikidata_qid)
        total = sum(len(ds) for ds in result.values())
        # 97+ ceremonies since 1929. If we get nothing or 1000s,
        # something's wrong with the query.
        self.assertGreater(total, 80)
        self.assertLess(total, 200)
