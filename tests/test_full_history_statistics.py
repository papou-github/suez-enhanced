"""Pure full-history Recorder batch selection regression tests."""
import ast
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "suez_enhanced"
source = (ROOT / "full_history_statistics.py").read_text()
tree = ast.parse(source)
fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "select_new_statistics")
namespace = {
    "date": date, "timedelta": timedelta, "isfinite": __import__("math").isfinite,
    "BATCH_DAYS": 14, "StatisticData": lambda **kw: SimpleNamespace(**kw),
    "local_midnight_utc": lambda day: datetime.combine(
        day + timedelta(days=1), datetime.min.time(), ZoneInfo("Europe/Paris")
    ).astimezone(timezone.utc),
}
exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), "<batch>", "exec"), namespace)
select = namespace["select_new_statistics"]


class FullHistoryTests(unittest.TestCase):
    def test_initial_batch_cumulative_and_gap(self):
        rows = {date(2024, 12, 31): 10, date(2025, 1, 1): 20, date(2025, 1, 3): 30}
        batch = select(rows, None, 0)
        self.assertEqual([x.sum for x in batch], [10, 30])
        self.assertEqual(batch[0].start.astimezone(ZoneInfo("Europe/Paris")).date(), date(2025, 1, 1))

    def test_resume_skips_existing_day(self):
        batch = select({date(2025, 1, 1): 10, date(2025, 1, 2): 20}, date(2025, 1, 1), 10)
        self.assertEqual(len(batch), 1)
        self.assertEqual(batch[0].sum, 30)

    def test_missing_next_day_never_skipped(self):
        self.assertEqual(select({date(2025, 1, 3): 10}, date(2025, 1, 1), 5), [])

    def test_bounded_batch(self):
        first = date(2025, 1, 1)
        rows = {first + timedelta(days=i): 1 for i in range(30)}
        self.assertEqual(len(select(rows, None, 0)), 14)

    def test_invalid_reading_rejected(self):
        with self.assertRaises(ValueError):
            select({date(2025, 1, 1): float("nan")}, None, 0)


if __name__ == "__main__":
    unittest.main()
