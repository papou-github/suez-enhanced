"""Pure unit tests for historical telemetry selection and time boundaries."""
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from importlib.util import spec_from_file_location, module_from_spec
import sys
import unittest

spec = spec_from_file_location("suez_history", Path(__file__).resolve().parents[1] / "custom_components/suez_enhanced/history.py")
history = module_from_spec(spec)
sys.modules[spec.name] = history
spec.loader.exec_module(history)


def measure(day, volume, index=None):
    return SimpleNamespace(date=day, volume=volume, index=index)


class HistoryTests(unittest.TestCase):
    def test_zero_is_real_consumption(self):
        self.assertEqual(history.daily_readings([measure(date(2026, 10, 17), 0)])[0].liters, 0)

    def test_reject_invalid_volume(self):
        self.assertEqual(history.daily_readings([measure(date(2026, 10, 17), float("inf"))]), [])
        self.assertEqual(history.daily_readings([measure(date(2026, 10, 17), -1)]), [])

    def test_duplicate_same_is_ok(self):
        self.assertEqual(len(history.daily_readings([measure(date(2026, 10, 17), 0)] * 2)), 1)

    def test_conflicting_duplicate_is_rejected(self):
        with self.assertRaises(ValueError):
            history.daily_readings([measure(date(2026, 10, 17), 0), measure(date(2026, 10, 17), 10)])

    def test_missing_day_stops_backfill(self):
        readings = history.daily_readings([
            measure(date(2026, 10, 17), 0),
            measure(date(2026, 10, 19), 10),
        ])
        selected = history.select_consecutive(readings, date(2026, 10, 16), date(2026, 10, 19))
        self.assertEqual([r.day for r in selected], [date(2026, 10, 17)])

    def test_index_mismatch_rejected(self):
        readings = history.daily_readings([
            measure(date(2026, 10, 16), 20, 1000),
            measure(date(2026, 10, 17), 50, 1020),
        ])
        with self.assertRaises(ValueError):
            history.validate_index_deltas(readings)

    def test_index_consistent(self):
        readings = history.daily_readings([
            measure(date(2026, 10, 16), 20, 1000),
            measure(date(2026, 10, 17), 50, 1050),
        ])
        history.validate_index_deltas(readings)

    def test_paris_dst_spring(self):
        a = history.local_midnight_utc(date(2026, 3, 28))
        b = history.local_midnight_utc(date(2026, 3, 29))
        self.assertEqual((b - a).total_seconds(), 23 * 3600)

    def test_paris_dst_fall(self):
        a = history.local_midnight_utc(date(2026, 10, 24))
        b = history.local_midnight_utc(date(2026, 10, 25))
        self.assertEqual((b - a).total_seconds(), 25 * 3600)


if __name__ == "__main__":
    unittest.main()
