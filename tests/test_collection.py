"""Tests for LazyDateMap, union(), and SpecialDays."""

import doctest
from datetime import date, datetime
from unittest import TestCase

import special_days
from special_days import (
    EVENT_REGISTRY,
    LazyDateMap,
    Oscars,
    SpecialDays,
    SuperBowl,
    lazy,
    union,
)


def load_tests(loader, tests, ignore):
    """Run package and module doctests alongside the regular suite."""
    tests.addTests(doctest.DocTestSuite(special_days))
    tests.addTests(doctest.DocTestSuite(lazy))
    return tests


class LazyDateMapTests(TestCase):
    """Read-only union view over date-keyed dict-likes."""

    def setUp(self):
        self.a = {date(2025, 1, 1): "New Year's"}
        self.b = {date(2025, 7, 4): "Independence"}
        self.m = LazyDateMap(self.a, self.b)

    def test_contains_finds_in_either_source(self):
        self.assertIn(date(2025, 1, 1), self.m)
        self.assertIn(date(2025, 7, 4), self.m)
        self.assertNotIn(date(2025, 5, 1), self.m)

    def test_contains_normalizes_datetime(self):
        self.assertIn(datetime(2025, 1, 1), self.m)

    def test_getitem_returns_first_match(self):
        self.assertEqual(self.m[date(2025, 1, 1)], "New Year's")
        self.assertEqual(self.m[date(2025, 7, 4)], "Independence")

    def test_getitem_raises_keyerror_for_missing(self):
        with self.assertRaises(KeyError):
            _ = self.m[date(2025, 5, 1)]

    def test_first_source_wins_on_collision(self):
        a = {date(2025, 1, 1): "first"}
        b = {date(2025, 1, 1): "second"}
        self.assertEqual(LazyDateMap(a, b)[date(2025, 1, 1)], "first")

    def test_get_with_default(self):
        self.assertEqual(self.m.get(date(2025, 5, 1)), None)
        self.assertEqual(self.m.get(date(2025, 5, 1), "x"), "x")

    def test_get_list_collects_from_all_sources(self):
        a = {date(2025, 1, 1): "A1"}
        b = {date(2025, 1, 1): "B1"}
        m = LazyDateMap(a, b)
        self.assertEqual(m.get_list(date(2025, 1, 1)), ["A1", "B1"])

    def test_get_list_delegates_to_source_get_list_if_available(self):
        class Multi:
            """Stand-in for holidays.HolidayBase that returns multiple names."""

            def __contains__(self, key):
                return key == date(2025, 1, 1)

            def __getitem__(self, key):
                return "Holiday1; Holiday2"

            def get_list(self, key):
                if key == date(2025, 1, 1):
                    return ["Holiday1", "Holiday2"]
                return []

            def __iter__(self):
                return iter([date(2025, 1, 1)])

        m = LazyDateMap(Multi(), {date(2025, 1, 1): "Super Bowl"})
        self.assertEqual(
            m.get_list(date(2025, 1, 1)),
            ["Holiday1", "Holiday2", "Super Bowl"],
        )

    def test_iteration_unions_keys_without_duplicates(self):
        a = {date(2025, 1, 1): "x"}
        b = {date(2025, 1, 1): "y", date(2025, 7, 4): "z"}
        self.assertEqual(
            set(LazyDateMap(a, b)),
            {date(2025, 1, 1), date(2025, 7, 4)},
        )


class UnionFunctionTests(TestCase):
    def test_returns_lazy_date_map(self):
        m = union({date(2025, 1, 1): "a"}, {date(2025, 7, 4): "b"})
        self.assertIsInstance(m, LazyDateMap)
        self.assertIn(date(2025, 1, 1), m)
        self.assertIn(date(2025, 7, 4), m)


class LazyDateMapComposesLazySourcesTests(TestCase):
    """A source's iteration is not forced; LazyDateMap mirrors whatever
    the source decides to expose via ``__iter__``. This matters for
    rule-driven sources like ``holidays.HolidayBase`` that only yield
    years that have been touched.
    """

    def test_iteration_only_yields_what_sources_expose(self):
        emitted: list[date] = []

        class TouchOnlyOnIter:
            def __contains__(self, key):
                return False

            def __iter__(self):
                return iter(emitted)

        source = TouchOnlyOnIter()
        m = LazyDateMap(source)
        self.assertEqual(list(m), [])
        emitted.append(date(2025, 1, 1))
        self.assertEqual(list(m), [date(2025, 1, 1)])


class SpecialDaysTests(TestCase):
    def test_default_constructor_uses_full_registry(self):
        sd = SpecialDays()
        self.assertEqual(len(sd.sources), len(EVENT_REGISTRY))

    def test_accepts_event_strings(self):
        sd = SpecialDays(events=["super_bowl"])
        self.assertIsInstance(sd.sources[0], SuperBowl)

    def test_unknown_string_raises_valueerror_with_known_list(self):
        with self.assertRaises(ValueError) as ctx:
            SpecialDays(events=["world_cup"])
        self.assertIn("world_cup", str(ctx.exception))
        self.assertIn("super_bowl", str(ctx.exception))

    def test_accepts_event_classes(self):
        sd = SpecialDays(events=[SuperBowl])
        self.assertIsInstance(sd.sources[0], SuperBowl)

    def test_accepts_already_instantiated_events(self):
        sb = SuperBowl()
        sd = SpecialDays(events=[sb])
        self.assertIs(sd.sources[0], sb)

    def test_lookups_flow_through_to_events(self):
        sd = SpecialDays(events=[SuperBowl])
        self.assertIn(date(2025, 2, 9), sd)
        self.assertEqual(sd[date(2025, 2, 9)], "Super Bowl")
        self.assertEqual(sd.get_list(date(2025, 2, 9)), ["Super Bowl"])

    def test_get_list_across_multiple_events(self):
        sd = SpecialDays()
        self.assertEqual(sd.get_list(date(2025, 2, 9)), ["Super Bowl"])
        self.assertEqual(sd.get_list(date(2025, 3, 2)), ["Academy Awards"])

    def test_mixed_inputs(self):
        sd = SpecialDays(events=["super_bowl", SuperBowl, SuperBowl()])
        self.assertEqual(len(sd.sources), 3)
        for src in sd.sources:
            self.assertIsInstance(src, SuperBowl)


class SpecialDaysHolidaysInteropTests(TestCase):
    """End-to-end of the emoji-by-name pattern, simulating holidays."""

    def test_user_pattern_works_with_lazy_union(self):
        # Simulate holidays.HolidayBase with a static dict.
        us_like = {date(2025, 7, 4): "Independence Day"}

        sd = SpecialDays(events=[SuperBowl, Oscars])
        combined = union(us_like, sd)

        EMOJI = {
            "Independence Day": "INDY",
            "Super Bowl": "SB",
            "Academy Awards": "OSC",
        }

        def get_special(d):
            return [
                {"name": n, "emoji": EMOJI[n]}
                for n in combined.get_list(d)
                if n in EMOJI
            ]

        self.assertEqual(
            get_special(date(2025, 7, 4)),
            [{"name": "Independence Day", "emoji": "INDY"}],
        )
        self.assertEqual(
            get_special(date(2025, 2, 9)),
            [{"name": "Super Bowl", "emoji": "SB"}],
        )
        self.assertEqual(
            get_special(date(2025, 3, 2)),
            [{"name": "Academy Awards", "emoji": "OSC"}],
        )
        self.assertEqual(get_special(date(2025, 5, 1)), [])
