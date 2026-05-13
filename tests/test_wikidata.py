"""Tests for the low-level Wikidata SPARQL client.

This module is not on the runtime lookup path; it's used by the
snapshot-build scripts and the opt-in live tests.
"""

import json
from datetime import date
from unittest import TestCase, mock
from urllib.error import HTTPError, URLError

from special_days.wikidata import (
    SPARQL_ENDPOINT,
    WikidataUnavailable,
    fetch_event_dates,
    parse_event_results,
    sparql_query,
)


def _mock_urlopen_returning(body_bytes):
    """Build a mock urlopen that returns a context-managed response."""
    response = mock.MagicMock()
    response.read.return_value = body_bytes
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return mock.MagicMock(return_value=response)


class SparqlQueryRequestTests(TestCase):
    def test_targets_wikidata_endpoint(self):
        body = json.dumps(
            {"head": {"vars": []}, "results": {"bindings": []}}
        ).encode()
        opener = _mock_urlopen_returning(body)
        with mock.patch("special_days.wikidata.urlopen", opener):
            sparql_query("SELECT * WHERE { ?s ?p ?o } LIMIT 1")
        request = opener.call_args[0][0]
        self.assertTrue(request.full_url.startswith(SPARQL_ENDPOINT))

    def test_sends_user_agent_identifying_package(self):
        body = json.dumps(
            {"head": {"vars": []}, "results": {"bindings": []}}
        ).encode()
        opener = _mock_urlopen_returning(body)
        with mock.patch("special_days.wikidata.urlopen", opener):
            sparql_query("ASK { ?s ?p ?o }")
        request = opener.call_args[0][0]
        ua = request.get_header("User-agent") or ""
        self.assertIn("special-days", ua)

    def test_requests_json_results_format(self):
        body = json.dumps(
            {"head": {"vars": []}, "results": {"bindings": []}}
        ).encode()
        opener = _mock_urlopen_returning(body)
        with mock.patch("special_days.wikidata.urlopen", opener):
            sparql_query("ASK { ?s ?p ?o }")
        request = opener.call_args[0][0]
        accept = request.get_header("Accept") or ""
        self.assertIn("application/sparql-results+json", accept)

    def test_returns_parsed_json(self):
        payload = {
            "head": {"vars": ["x"]},
            "results": {"bindings": [{"x": {"value": "hi"}}]},
        }
        opener = _mock_urlopen_returning(json.dumps(payload).encode())
        with mock.patch("special_days.wikidata.urlopen", opener):
            result = sparql_query("ASK { ?s ?p ?o }")
        self.assertEqual(result, payload)


class SparqlQueryErrorTests(TestCase):
    def test_http_error_wrapped_in_wikidata_unavailable(self):
        err = HTTPError("http://x", 503, "Service Unavailable", {}, None)
        with mock.patch("special_days.wikidata.urlopen", side_effect=err):
            with self.assertRaises(WikidataUnavailable):
                sparql_query("ASK { ?s ?p ?o }")

    def test_url_error_wrapped_in_wikidata_unavailable(self):
        with mock.patch(
            "special_days.wikidata.urlopen",
            side_effect=URLError("offline"),
        ):
            with self.assertRaises(WikidataUnavailable):
                sparql_query("ASK { ?s ?p ?o }")

    def test_invalid_json_wrapped_in_wikidata_unavailable(self):
        opener = _mock_urlopen_returning(b"<html>oops</html>")
        with mock.patch("special_days.wikidata.urlopen", opener):
            with self.assertRaises(WikidataUnavailable):
                sparql_query("ASK { ?s ?p ?o }")


class ParseEventResultsTests(TestCase):
    """Test parsing of SPARQL JSON results into ``{year: [date, ...]}``."""

    def _binding(self, iso_date, label="Event"):
        return {
            "item": {
                "type": "uri",
                "value": "http://www.wikidata.org/entity/Q1",
            },
            "itemLabel": {
                "xml:lang": "en",
                "type": "literal",
                "value": label,
            },
            "date": {
                "datatype": "http://www.w3.org/2001/XMLSchema#dateTime",
                "type": "literal",
                "value": iso_date,
            },
        }

    def test_parses_year_to_dates(self):
        results = {
            "head": {"vars": ["item", "itemLabel", "date"]},
            "results": {
                "bindings": [
                    self._binding("1967-01-15T00:00:00Z", "Super Bowl I"),
                    self._binding("2025-02-09T00:00:00Z", "Super Bowl LIX"),
                ]
            },
        }
        parsed = parse_event_results(results)
        self.assertEqual(parsed[1967], [date(1967, 1, 15)])
        self.assertEqual(parsed[2025], [date(2025, 2, 9)])

    def test_handles_empty_results(self):
        results = {
            "head": {"vars": ["item", "itemLabel", "date"]},
            "results": {"bindings": []},
        }
        self.assertEqual(parse_event_results(results), {})

    def test_ignores_bindings_missing_date(self):
        results = {
            "head": {"vars": ["item", "itemLabel", "date"]},
            "results": {
                "bindings": [
                    {"item": {"value": "x"}, "itemLabel": {"value": "y"}},
                    self._binding("2025-02-09T00:00:00Z"),
                ]
            },
        }
        parsed = parse_event_results(results)
        self.assertEqual(parsed, {2025: [date(2025, 2, 9)]})

    def test_two_events_in_same_year_preserved_and_sorted(self):
        """Two ceremonies in one calendar year (e.g. Academy Awards in
        1930) must both make it through, in chronological order."""
        results = {
            "head": {"vars": ["item", "itemLabel", "date"]},
            "results": {
                "bindings": [
                    self._binding("1930-11-05T00:00:00Z", "3rd"),
                    self._binding("1930-04-03T00:00:00Z", "2nd"),
                ]
            },
        }
        parsed = parse_event_results(results)
        self.assertEqual(parsed[1930], [date(1930, 4, 3), date(1930, 11, 5)])

    def test_duplicate_dates_in_year_are_deduped(self):
        results = {
            "head": {"vars": ["item", "itemLabel", "date"]},
            "results": {
                "bindings": [
                    self._binding("2025-02-09T00:00:00Z"),
                    self._binding("2025-02-09T00:00:00Z"),
                ]
            },
        }
        self.assertEqual(
            parse_event_results(results), {2025: [date(2025, 2, 9)]}
        )


class QidValidationTests(TestCase):
    def test_rejects_bad_qids(self):
        for bad in ["", "Q", "Q0", "Q01", "Q1a", "P31", "garbage", "Q-1"]:
            with self.assertRaises(ValueError, msg=bad):
                fetch_event_dates(bad)

    def test_accepts_valid_qids(self):
        body = json.dumps(
            {"head": {"vars": []}, "results": {"bindings": []}}
        ).encode()
        opener = _mock_urlopen_returning(body)
        with mock.patch("special_days.wikidata.urlopen", opener):
            # Just shouldn't raise.
            fetch_event_dates("Q32096")
            fetch_event_dates("Q19020")


class QueryFiltersDatePrecisionTests(TestCase):
    """The SPARQL query must filter to day-precision dates only."""

    def test_query_constrains_time_precision(self):
        body = json.dumps(
            {"head": {"vars": []}, "results": {"bindings": []}}
        ).encode()
        opener = _mock_urlopen_returning(body)
        with mock.patch("special_days.wikidata.urlopen", opener):
            fetch_event_dates("Q32096")
        url = opener.call_args[0][0].full_url
        self.assertIn("timePrecision", url)
        self.assertIn("11", url)

    def test_query_excludes_deprecated_rank(self):
        body = json.dumps(
            {"head": {"vars": []}, "results": {"bindings": []}}
        ).encode()
        opener = _mock_urlopen_returning(body)
        with mock.patch("special_days.wikidata.urlopen", opener):
            fetch_event_dates("Q32096")
        url = opener.call_args[0][0].full_url
        self.assertIn("rank", url)
        self.assertIn("DeprecatedRank", url)


class EventFetchFromWikidataTests(TestCase):
    """``Event.fetch_from_wikidata`` is the opt-in runtime-refresh path."""

    def test_passes_event_qid_through_to_fetch_event_dates(self):
        from special_days import super_bowl

        body = json.dumps(
            {
                "head": {"vars": ["item", "itemLabel", "date"]},
                "results": {
                    "bindings": [
                        {"date": {"value": "2025-02-09T00:00:00Z"}},
                    ]
                },
            }
        ).encode()
        opener = _mock_urlopen_returning(body)
        with mock.patch("special_days.wikidata.urlopen", opener):
            result = super_bowl.EVENT.fetch_from_wikidata()
        url = opener.call_args[0][0].full_url
        self.assertIn(super_bowl.EVENT.wikidata_qid, url)
        self.assertEqual(result, {2025: [date(2025, 2, 9)]})

    def test_does_not_mutate_event_state(self):
        from special_days import super_bowl

        before = super_bowl.EVENT.all_known()
        body = json.dumps(
            {"head": {"vars": []}, "results": {"bindings": []}}
        ).encode()
        opener = _mock_urlopen_returning(body)
        with mock.patch("special_days.wikidata.urlopen", opener):
            super_bowl.EVENT.fetch_from_wikidata()
        # Fetch returns data; it does not silently replace the snapshot.
        self.assertEqual(super_bowl.EVENT.all_known(), before)
