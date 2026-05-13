"""Tests for the on-disk cache."""

import json
import tempfile
from datetime import date
from pathlib import Path
from unittest import TestCase, mock

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


class CacheWriteBestEffortTests(TestCase):
    """write_cache must not crash when the destination is unwritable.

    Users in restricted environments (read-only filesystems, sandboxes,
    containers without HOME, etc.) shouldn't see a PermissionError
    propagate up to their lookup call -- the cache is an optimization,
    not a correctness requirement.
    """

    def test_swallows_permission_error_on_mkdir(self):
        # Patch mkdir to raise PermissionError -- simulates a parent
        # directory we have no write access to.
        with mock.patch.object(
            Path, "mkdir", side_effect=PermissionError("denied")
        ):
            # Should not raise.
            write_cache("/some/unwritable/path.json", {2025: date(2025, 2, 9)})

    def test_swallows_permission_error_on_write_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.json"
            with mock.patch.object(
                Path, "write_text", side_effect=PermissionError("denied")
            ):
                # Should not raise.
                write_cache(path, {2025: date(2025, 2, 9)})

    def test_swallows_generic_oserror(self):
        with mock.patch.object(
            Path, "mkdir", side_effect=OSError("anything goes wrong")
        ):
            write_cache("/some/path.json", {2025: date(2025, 2, 9)})
