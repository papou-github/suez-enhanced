"""Merge daily readings for yearly summaries without altering Recorder."""

from types import SimpleNamespace


def merge_year_readings(recorded, recent):
    """Recorder wins on overlap; API only fills missing days."""
    by_day = {
        reading.day: SimpleNamespace(
            date=reading.day,
            volume=reading.liters,
            index=reading.meter_index_liters,
        )
        for reading in recent
    }
    by_day.update({
        reading.day: SimpleNamespace(
            date=reading.day,
            volume=reading.liters,
            index=reading.meter_index_liters,
        )
        for reading in recorded
    })
    return [by_day[day] for day in sorted(by_day)]
