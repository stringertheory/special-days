"""Tests for the on-disk cache."""

import json
import tempfile
from datetime import date
from pathlib import Path
from unittest import TestCase

from special_days._cache import read_cache, write_cache


class CacheRoundTripTests(TestCase):
    def test_writes_and_reads_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.json"
            data = {2025: date(2025, 2, 9), 2026: date(2026, 2, 8)}
            write_cache(path, data)
            self.assertEqual(read_cache(path), data)

    def test_create_parent_directories_on_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "deep" / "events.json"
            write_cache(path, {2025: date(2025, 2, 9)})
            self.assertTrue(path.exists())


class CacheMissingTests(TestCase):
    def test_returns_empty_dict_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nope.json"
            self.assertEqual(read_cache(path), {})

    def test_returns_empty_dict_when_file_unreadable_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("not json")
            self.assertEqual(read_cache(path), {})

    def test_returns_empty_dict_when_file_has_wrong_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wrong.json"
            path.write_text(json.dumps(["not", "a", "dict"]))
            self.assertEqual(read_cache(path), {})
