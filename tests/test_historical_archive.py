"""Mocked Home Assistant Store tests for the historical archive."""
import asyncio
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "suez_enhanced"

pkg = sys.modules.setdefault("suez_enhanced", types.ModuleType("suez_enhanced"))
pkg.__path__ = [str(ROOT)]
ha = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
ha.__path__ = []
helpers = sys.modules.setdefault("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
helpers.__path__ = []
storage = types.ModuleType("homeassistant.helpers.storage")


class FakeStore:
    payload = None

    def __init__(self, hass, version, key):
        self.key = key

    async def async_load(self):
        import copy
        return copy.deepcopy(self.payload)

    async def async_save(self, value):
        import copy
        self.__class__.payload = copy.deepcopy(value)


storage.Store = FakeStore
sys.modules["homeassistant.helpers.storage"] = storage

def load_module(name):
    fullname = "suez_enhanced." + name
    if fullname in sys.modules:
        return sys.modules[fullname]
    spec = importlib.util.spec_from_file_location(fullname, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[fullname] = module
    spec.loader.exec_module(module)
    return module


load_module("history")
archive_module = load_module("historical_archive")


class ArchiveTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        FakeStore.payload = None
        self.archive = archive_module.HistoricalArchive(None, "entry", "3197811457")

    async def test_empty_windows_survive_restart(self):
        await self.archive.save_window(date(2025, 12, 1), date(2025, 12, 14), [])
        self.assertEqual((await self.archive.load())["empty_windows"], 1)
        restarted = archive_module.HistoricalArchive(None, "entry", "3197811457")
        self.assertEqual((await restarted.load())["empty_windows"], 1)
        await restarted.save_window(date(2025, 11, 17), date(2025, 11, 30), [])
        self.assertEqual((await restarted.load())["empty_windows"], 2)

    async def test_nonempty_window_resets_empty_count(self):
        await self.archive.save_window(date(2025, 12, 1), date(2025, 12, 14), [])
        measure = SimpleNamespace(date=date(2025, 11, 30), volume=120.0, index=1234.0)
        data = await self.archive.save_window(date(2025, 11, 17), date(2025, 11, 30), [measure])
        self.assertEqual(data["empty_windows"], 0)
        self.assertEqual(data["days"]["2025-11-30"], 120.0)

    async def test_conflict_preserves_existing_checkpoint(self):
        first = SimpleNamespace(date=date(2025, 11, 30), volume=120.0, index=None)
        second = SimpleNamespace(date=date(2025, 11, 30), volume=121.0, index=None)
        await self.archive.save_window(date(2025, 11, 17), date(2025, 11, 30), [first])
        before = await self.archive.load()
        with self.assertRaises(ValueError):
            await self.archive.save_window(date(2025, 11, 17), date(2025, 11, 30), [second])
        self.assertEqual(await self.archive.load(), before)

    async def test_fourteen_day_window_enforced(self):
        with self.assertRaises(ValueError):
            await self.archive.save_window(date(2025, 11, 1), date(2025, 11, 15), [])


if __name__ == "__main__":
    unittest.main()
