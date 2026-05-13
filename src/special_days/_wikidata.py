"""Minimal Wikidata SPARQL client (stdlib only).

This module is **not** on the runtime lookup path. It exists for the
snapshot-build scripts and the opt-in live tests. Users should never
need to call into it; the wheel ships everything Wikidata told us last
build.

The SPARQL Query Results JSON Format we parse is a W3C standard
(https://www.w3.org/TR/sparql11-results-json/), so the response shape is
stable. The query itself is what's most likely to need updating over the
years if Wikidata's modeling of an event series changes; see
:data:`EVENT_DATES_QUERY` below.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import __version__

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# Wikidata asks API clients to identify themselves so abuse can be
# diagnosed and contacted: https://meta.wikimedia.org/wiki/User-Agent_policy
#
# If you fork this package, change the URL in the user-agent below to
# point at your fork. Leaving the upstream URL means an abuse complaint
# about your fork's traffic lands in our inbox, not yours.
_USER_AGENT = (
    f"special-days/{__version__} "
    "(+https://github.com/stringertheory/special-days)"
)

# Match any item that is related to a series Q-ID through one of the
# three predicates most commonly used for "this is one installment of
# that series" in Wikidata:
#   P31  - instance of
#   P361 - part of
#   P179 - part of the series
#
# We UNION all three because conventions differ across event types and
# can drift over time. If a future Wikidata reshape breaks this query,
# update it here and cut a new release.
#
# Wikidata stores P585 ("point in time") with a precision qualifier:
#   11 = day, 10 = month, 9 = year
# An upcoming event announced only to the month (e.g. "February 2029")
# is stored with precision 10 and a placeholder day (YYYY-MM-01). We
# go through the statement-level path (p:P585 / psv:P585) so we can
# read wikibase:timePrecision, then filter to day-precision (>=11)
# values only. Without this filter, those placeholders would silently
# leak into our output as bogus Feb-1 (etc.) dates.
#
# We also filter out statements at deprecated rank. Wikidata uses
# deprecated rank to mark known-wrong values while preserving them in
# history; consumers are expected to honor that. Honoring rank means
# we don't have to maintain event-specific workarounds for individual
# bad claims -- editors fix it upstream, our query stops returning it.
EVENT_DATES_QUERY = """\
SELECT ?item ?itemLabel ?date WHERE {{
  {{ ?item wdt:P31 wd:{qid} . }}
  UNION
  {{ ?item wdt:P361 wd:{qid} . }}
  UNION
  {{ ?item wdt:P179 wd:{qid} . }}
  ?item p:P585 ?statement .
  ?statement psv:P585 ?dateValue .
  ?dateValue wikibase:timeValue ?date .
  ?dateValue wikibase:timePrecision ?precision .
  ?statement wikibase:rank ?rank .
  FILTER(?precision >= 11)
  FILTER(?rank != wikibase:DeprecatedRank)
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
ORDER BY ?date
"""

# Wikidata QIDs are "Q" followed by a positive integer.
_QID_RE = re.compile(r"^Q[1-9]\d*$")


class WikidataUnavailable(Exception):
    """Raised when we cannot get a usable response from Wikidata."""


def sparql_query(query: str, timeout: float = 15) -> dict[str, Any]:
    """Run a SPARQL query against Wikidata and return parsed JSON.

    Raises WikidataUnavailable on network / HTTP / JSON errors.
    """
    url = SPARQL_ENDPOINT + "?" + urlencode({"query": query})
    request = Request(url)
    request.add_header("Accept", "application/sparql-results+json")
    request.add_header("User-Agent", _USER_AGENT)
    try:
        # The URL is built from a hardcoded https endpoint plus a
        # urlencoded SPARQL query; no caller-controlled scheme is
        # reachable. Suppressing both ruff (S310) and bandit (B310)
        # for the same reason.
        with urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
            body = response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise WikidataUnavailable(str(exc)) from exc
    try:
        return json.loads(body)  # type: ignore[no-any-return]
    except (ValueError, UnicodeDecodeError) as exc:
        raise WikidataUnavailable(
            f"non-JSON response from Wikidata: {exc}"
        ) from exc


def parse_event_results(results: dict[str, Any]) -> dict[int, list[date]]:
    """Turn a SPARQL JSON response into a ``{year: [date, ...]}`` mapping.

    Multiple dates in the same calendar year are preserved (e.g. the
    2nd and 3rd Academy Awards both in 1930). Within a year, dates are
    sorted ascending and de-duplicated.
    """
    out: dict[int, set[date]] = {}
    for binding in results.get("results", {}).get("bindings", []):
        raw = binding.get("date", {}).get("value")
        if not raw:
            continue
        try:
            d = _parse_xsd_date(raw)
        except ValueError:
            continue
        out.setdefault(d.year, set()).add(d)
    return {y: sorted(ds) for y, ds in out.items()}


def _parse_xsd_date(value: str) -> date:
    """Parse a Wikidata xsd:dateTime literal into a ``date``.

    Wikidata emits values like '2025-02-09T00:00:00Z'. Historical items
    can have negative years or unusual precision; the SPARQL query
    filters those out, so we only handle the common modern case here
    and let anything weird raise ValueError.
    """
    # Strip a trailing Z so fromisoformat (which doesn't accept Z until
    # Python 3.11) can handle older interpreters.
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).date()


def fetch_event_dates(series_qid: str) -> dict[int, list[date]]:
    """Fetch all known event dates for the given Wikidata series Q-ID.

    Returns ``{year: [date, ...]}``. Raises ``ValueError`` if
    ``series_qid`` isn't a syntactically valid QID and
    ``WikidataUnavailable`` on network/parse failure.
    """
    if not _QID_RE.match(series_qid):
        raise ValueError(f"invalid Wikidata QID: {series_qid!r}")
    query = EVENT_DATES_QUERY.format(qid=series_qid)
    return parse_event_results(sparql_query(query))


def fetch_super_bowl_dates() -> dict[int, list[date]]:
    """Convenience wrapper: all known Super Bowl dates from Wikidata."""
    # Q32096 is the Wikidata item for "Super Bowl".
    return fetch_event_dates("Q32096")


def fetch_oscars_dates() -> dict[int, list[date]]:
    """Convenience wrapper: all known Academy Awards ceremony dates."""
    # Q19020 is the Wikidata item for "Academy Awards".
    return fetch_event_dates("Q19020")
