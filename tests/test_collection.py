"""Tests for LazyDateMap, union(), and SpecialDays."""

from datetime import date
from unittest import TestCase, mock

from special_days import (
    EVENT_REGISTRY,
    LazyDateMap,
    SpecialDays,
    SuperBowl,
    union,
)


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


class LazyDateMapRefreshTests(TestCase):
    def test_refresh_calls_refresh_on_each_source_that_has_one(self):
        a = mock.MagicMock()
        b = mock.MagicMock()
        m = LazyDateMap(a, b)
        m.refresh()
        a.refresh.assert_called_once()
        b.refresh.assert_called_once()

    def test_refresh_skips_sources_without_a_refresh_method(self):
        plain = {date(2025, 1, 1): "x"}  # no .refresh
        b = mock.MagicMock()
        m = LazyDateMap(plain, b)
        m.refresh()  # must not raise
        b.refresh.assert_called_once()

    def test_refresh_propagates_errors_from_sources(self):
        a = mock.MagicMock()
        a.refresh.side_effect = RuntimeError("disabled")
        b = mock.MagicMock()
        m = LazyDateMap(a, b)
        with self.assertRaises(RuntimeError):
            m.refresh()
        # b was not refreshed because a raised first
        b.refresh.assert_not_called()


class SpecialDaysRefreshTests(TestCase):
    def test_special_days_inherits_refresh_from_lazy_date_map(self):
        sb = mock.MagicMock(spec=SuperBowl)
        sd = SpecialDays(events=[sb])
        sd.refresh()
        sb.refresh.assert_called_once()


class LazyDateMapPreservesLazinessTests(TestCase):
    """Membership queries must not force eager population of event sources."""

    def test_in_only_loads_year_in_question(self):
        sb = SuperBowl()
        m = LazyDateMap(sb)
        _ = date(2025, 2, 9) in m
        self.assertEqual(set(sb), {date(2025, 2, 9)})  # 2025 loaded
        # Other years not yet loaded — iter(sb) shouldn't have any.

    def test_iteration_does_not_force_a_load(self):
        sb = SuperBowl()
        m = LazyDateMap(sb)
        self.assertEqual(list(m), [])  # sb is empty; iteration empties


class SpecialDaysTests(TestCase):
    def test_default_constructor_uses_full_registry(self):
        sd = SpecialDays()
        # Every registered event should be an underlying source.
        self.assertEqual(len(sd._sources), len(EVENT_REGISTRY))

    def test_accepts_event_strings(self):
        sd = SpecialDays(events=["super_bowl"])
        self.assertIsInstance(sd._sources[0], SuperBowl)

    def test_unknown_string_raises_valueerror_with_known_list(self):
        with self.assertRaises(ValueError) as ctx:
            SpecialDays(events=["world_cup"])
        self.assertIn("world_cup", str(ctx.exception))
        self.assertIn("super_bowl", str(ctx.exception))

    def test_accepts_event_classes(self):
        sd = SpecialDays(events=[SuperBowl])
        self.assertIsInstance(sd._sources[0], SuperBowl)

    def test_accepts_already_instantiated_events(self):
        sb = SuperBowl(allow_network=False)
        sd = SpecialDays(events=[sb])
        self.assertIs(sd._sources[0], sb)

    def test_propagates_allow_network_to_resolved_events(self):
        sd = SpecialDays(events=["super_bowl"], allow_network=False)
        self.assertFalse(sd._sources[0]._allow_network)

    def test_lookups_flow_through_to_events(self):
        sd = SpecialDays(events=[SuperBowl])
        self.assertIn(date(2025, 2, 9), sd)
        self.assertEqual(sd[date(2025, 2, 9)], "Super Bowl")
        self.assertEqual(sd.get_list(date(2025, 2, 9)), ["Super Bowl"])

    def test_mixed_inputs(self):
        sd = SpecialDays(
            events=["super_bowl", SuperBowl, SuperBowl(allow_network=False)]
        )
        self.assertEqual(len(sd._sources), 3)
        for src in sd._sources:
            self.assertIsInstance(src, SuperBowl)


class SpecialDaysHolidaysInteropTests(TestCase):
    """End-to-end of the emoji-by-name pattern, simulating holidays."""

    def test_user_pattern_works_with_lazy_union(self):
        # Simulate holidays.HolidayBase with a static dict.
        us_like = {date(2025, 7, 4): "Independence Day"}

        # Patch the network so the SuperBowl class doesn't go online.
        with mock.patch(
            "special_days.super_bowl._fetch_from_wikidata"
        ) as fetch:
            fetch.return_value = {}
            sd = SpecialDays(events=[SuperBowl])
            combined = union(us_like, sd)

            EMOJI = {
                "Independence Day": "🎆",
                "Super Bowl": "🏈",
            }

            def get_special(d):
                return [
                    {"name": n, "emoji": EMOJI[n]}
                    for n in combined.get_list(d)
                    if n in EMOJI
                ]

            self.assertEqual(
                get_special(date(2025, 7, 4)),
                [{"name": "Independence Day", "emoji": "🎆"}],
            )
            self.assertEqual(
                get_special(date(2025, 2, 9)),
                [{"name": "Super Bowl", "emoji": "🏈"}],
            )
            self.assertEqual(get_special(date(2025, 5, 1)), [])
