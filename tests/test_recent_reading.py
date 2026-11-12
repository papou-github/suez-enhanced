"""Regression tests for provisional SUEZ zero values."""
from datetime import date, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/suez_enhanced/recent_reading.py"
spec = spec_from_file_location("recent_reading_test", SOURCE)
module = module_from_spec(spec)
spec.loader.exec_module(module)


def measure(day, volume, index):
    return SimpleNamespace(date=date.fromisoformat(day), volume=volume, index=index)


class RecentReadingTests(unittest.TestCase):
    def setUp(self):
        self.day = date(2026, 11, 11)

    def test_provisional_zero_is_not_confirmed(self):
        rows = [measure("2026-11-10", 150, 482905),
                measure("2026-11-11", 0, None)]
        self.assertIsNone(module.confirmed_yesterday(rows, self.day))
        self.assertEqual(len(module.without_provisional_yesterday(rows, self.day)), 1)

    def test_real_zero_with_index_is_confirmed(self):
        rows = [measure("2026-11-11", 0, 482905)]
        self.assertIs(module.confirmed_yesterday(rows, self.day), rows[0])
        self.assertEqual(module.without_provisional_yesterday(rows, self.day), rows)

    def test_published_positive_volume_is_confirmed_without_index(self):
        rows = [measure("2026-11-11", 146, None)]
        self.assertIs(module.confirmed_yesterday(rows, self.day), rows[0])

    def test_missing_yesterday_does_not_change_other_days(self):
        rows = [measure("2026-11-10", 120, None)]
        self.assertIsNone(module.confirmed_yesterday(rows, self.day))
        self.assertEqual(module.without_provisional_yesterday(rows, self.day), rows)

    def test_provisional_zero_not_reused_when_api_updates(self):
        cached = [measure("2026-11-11", 0, None)]
        refreshed = [measure("2026-11-11", 146, None)]
        self.assertIsNone(module.confirmed_yesterday(cached, self.day))
        self.assertEqual(module.confirmed_yesterday(refreshed, self.day).volume, 146)


if __name__ == "__main__":
    unittest.main()
