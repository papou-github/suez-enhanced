"""Regression: historical daily values must not double count month-end sums."""
import ast
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "suez_enhanced"
tree = ast.parse((ROOT / "recorder_history.py").read_text())
fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
          and n.name == "async_recorder_daily_readings")
PARIS = ZoneInfo("Europe/Paris")


class FakeRecorder:
    async def async_add_executor_job(self, function, *args):
        return function(*args)


def fake_statistics(hass, start, end, statistic_ids, period, units, types):
    assert types == {"state"}
    def point(day, state):
        timestamp = datetime.combine(day + timedelta(days=1), datetime.min.time(), PARIS)
        return {"start": timestamp.timestamp(), "state": state}
    return {
        "suez_water:123_water_consumption_statistics": [
            point(datetime(2024, 10, 30).date(), 236),
            point(datetime(2024, 10, 31).date(), 318),
            point(datetime(2024, 11, 1).date(), 237),
        ],
        "suez_enhanced:123_full_history": [
            point(datetime(2024, 10, 31).date(), 318),
        ],
    }


namespace = {
    "datetime": datetime, "timedelta": timedelta, "timezone": timezone,
    "PARIS": PARIS, "isfinite": __import__("math").isfinite,
    "get_instance": lambda hass: FakeRecorder(),
    "statistics_during_period": fake_statistics,
    "legacy_statistic_id": lambda counter: f"suez_water:{counter}_water_consumption_statistics",
    "full_history_statistic_id": lambda counter: f"suez_enhanced:{counter}_full_history",
    "DailyReading": lambda day, liters, index: SimpleNamespace(day=day, liters=liters),
}
exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])),
             "<recorder_history>", "exec"), namespace)


class MonthEndRegressionTests(unittest.TestCase):
    def test_month_end_state_not_doubled_by_legacy_sum(self):
        readings = asyncio.run(namespace["async_recorder_daily_readings"](object(), "123", 2024))
        by_day = {r.day.isoformat(): r.liters for r in readings}
        self.assertEqual(by_day["2024-10-31"], 318)
        self.assertEqual(by_day["2024-10-30"], 236)
        self.assertEqual(by_day["2024-11-01"], 237)
        self.assertEqual(sum(by_day.values()), 791)

    def test_year_boundary_is_not_lost(self):
        readings = asyncio.run(namespace["async_recorder_daily_readings"](object(), "123", 2024))
        self.assertNotIn("2025-01-01", {r.day.isoformat() for r in readings})


if __name__ == "__main__":
    unittest.main()
