"""Regression tests for pure daily-history selection and calendar summaries.

Run with: python -m unittest discover -s tests -p 'test_history_regression.py'
"""
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "suez_enhanced"
# Import pure helpers without requiring a running Home Assistant installation.
pkg = types.ModuleType("suez_enhanced")
pkg.__path__ = [str(ROOT)]
sys.modules.setdefault("suez_enhanced", pkg)
spec = importlib.util.spec_from_file_location("suez_enhanced.history", ROOT / "history.py")
history = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = history
spec.loader.exec_module(history)


class HistoryRegressionTests(unittest.TestCase):
    def measure(self, day, volume, index=None):
        return SimpleNamespace(date=day, volume=volume, index=index)

    def test_missing_day_stops_append_without_zero_fill(self):
        readings = history.daily_readings([
            self.measure(date(2026, 1, 2), 10),
            self.measure(date(2026, 1, 4), 20),
        ])
        selected = history.select_consecutive(readings, date(2026, 1, 1), date(2026, 1, 5))
        self.assertEqual([r.day for r in selected], [date(2026, 1, 2)])

    def test_duplicate_identical_accepted_conflict_rejected(self):
        day = date(2026, 1, 2)
        self.assertEqual(len(history.daily_readings([self.measure(day, 2), self.measure(day, 2)])), 1)
        with self.assertRaises(ValueError):
            history.daily_readings([self.measure(day, 2), self.measure(day, 3)])

    def test_invalid_values_excluded(self):
        day = date(2026, 1, 2)
        self.assertEqual(history.daily_readings([
            self.measure(day, -1), self.measure(day, float("nan"))
        ]), [])

    def test_dst_paris_midnight_mapping(self):
        for day in (date(2026, 3, 28), date(2026, 3, 29),
                    date(2026, 10, 24), date(2026, 10, 25)):
            utc = history.local_midnight_utc(day)
            self.assertEqual(utc.astimezone(history.PARIS).date(), day + timedelta(days=1))
            self.assertEqual(utc.astimezone(history.PARIS).hour, 0)

    def test_index_delta_validation(self):
        good = history.daily_readings([
            self.measure(date(2026, 1, 1), 5, 100),
            self.measure(date(2026, 1, 2), 7, 107),
        ])
        history.validate_index_deltas(good)
        bad = history.daily_readings([
            self.measure(date(2026, 1, 1), 5, 100),
            self.measure(date(2026, 1, 2), 7, 120),
        ])
        with self.assertRaises(ValueError):
            history.validate_index_deltas(bad)


if __name__ == "__main__":
    unittest.main()
