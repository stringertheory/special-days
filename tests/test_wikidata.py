"""Tests for the low-level Wikidata SPARQL client."""

import json
from datetime import date
from unittest import TestCase, mock
from urllib.error import HTTPError, URLError

from special_days._wikidata import (
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
        with mock.patch("special_days._wikidata.urlopen", opener):
            sparql_query("SELECT * WHERE { ?s ?p ?o } LIMIT 1")
        request = opener.call_args[0][0]
        self.assertTrue(request.full_url.startswith(SPARQL_ENDPOINT))

    def test_sends_user_agent_identifying_package(self):
        body = json.dumps(
            {"head": {"vars": []}, "results": {"bindings": []}}
        ).encode()
        opener = _mock_urlopen_returning(body)
        with mock.patch("special_days._wikidata.urlopen", opener):
            sparql_query("ASK { ?s ?p ?o }")
        request = opener.call_args[0][0]
        ua = request.get_header("User-agent") or ""
        self.assertIn("special-days", ua)

    def test_requests_json_results_format(self):
        body = json.dumps(
            {"head": {"vars": []}, "results": {"bindings": []}}
        ).encode()
        opener = _mock_urlopen_returning(body)
        with mock.patch("special_days._wikidata.urlopen", opener):
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
        with mock.patch("special_days._wikidata.urlopen", opener):
            result = sparql_query("ASK { ?s ?p ?o }")
        self.assertEqual(result, payload)


class SparqlQueryErrorTests(TestCase):
    def test_http_error_wrapped_in_wikidata_unavailable(self):
        err = HTTPError("http://x", 503, "Service Unavailable", {}, None)
        with mock.patch("special_days._wikidata.urlopen", side_effect=err):
            with self.assertRaises(WikidataUnavailable):
                sparql_query("ASK { ?s ?p ?o }")

    def test_url_error_wrapped_in_wikidata_unavailable(self):
        with mock.patch(
            "special_days._wikidata.urlopen",
            side_effect=URLError("offline"),
        ):
            with self.assertRaises(WikidataUnavailable):
                sparql_query("ASK { ?s ?p ?o }")

    def test_invalid_json_wrapped_in_wikidata_unavailable(self):
        opener = _mock_urlopen_returning(b"<html>oops</html>")
        with mock.patch("special_days._wikidata.urlopen", opener):
            with self.assertRaises(WikidataUnavailable):
                sparql_query("ASK { ?s ?p ?o }")


class ParseEventResultsTests(TestCase):
    """Test parsing of SPARQL JSON results into {year: date} mapping.

    Response shape follows the W3C SPARQL 1.1 Query Results JSON format
    (https://www.w3.org/TR/sparql11-results-json/).
    """

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

    def test_parses_year_to_date(self):
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
        self.assertEqual(parsed[1967], date(1967, 1, 15))
        self.assertEqual(parsed[2025], date(2025, 2, 9))

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
        self.assertEqual(parsed, {2025: date(2025, 2, 9)})

    def test_when_two_events_in_same_year_keeps_first(self):
        """Two events of the same kind in one calendar year is unusual
        but possible (e.g. World Series rescheduled). First wins so the
        result is deterministic; callers can use raw results if needed.
        """
        results = {
            "head": {"vars": ["item", "itemLabel", "date"]},
            "results": {
                "bindings": [
                    self._binding("2025-01-05T00:00:00Z", "A"),
                    self._binding("2025-12-20T00:00:00Z", "B"),
                ]
            },
        }
        parsed = parse_event_results(results)
        self.assertEqual(parsed, {2025: date(2025, 1, 5)})


class QueryFiltersDatePrecisionTests(TestCase):
    """The SPARQL query must filter to day-precision dates only.

    Wikidata stores P585 ("point in time") values with a precision
    qualifier: 11 = day, 10 = month, 9 = year. When a future event has
    only been announced down to the month, Wikidata returns the date as
    YYYY-MM-01 with precision 10. Without filtering, those placeholders
    silently leak into our results as bogus Feb-1 (etc.) dates.
    """

    def test_query_constrains_time_precision(self):
        body = json.dumps(
            {"head": {"vars": []}, "results": {"bindings": []}}
        ).encode()
        opener = _mock_urlopen_returning(body)
        with mock.patch("special_days._wikidata.urlopen", opener):
            fetch_event_dates("Q32096")
        url = opener.call_args[0][0].full_url
        # Both the precision predicate and the day-precision threshold
        # (11) must appear in the query. Asserting substrings keeps the
        # test resilient to formatting / variable-name changes.
        self.assertIn("timePrecision", url)
        self.assertIn("11", url)
