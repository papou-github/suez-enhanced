"""Pure, read-only consumption summaries from confirmed SUEZ daily readings."""
from __future__ import annotations

from datetime import date, timedelta
from math import isfinite

from .history import daily_readings


def consumption_summary(measures: list, today: date, price_per_m3: float) -> dict:
    """Return None for incomplete periods, never interpret missing days as zero."""
    if not isfinite(price_per_m3) or price_per_m3 < 0:
        raise ValueError("Water price must be a finite non-negative number")
    readings = {r.day: r.liters for r in daily_readings(measures)}
    cutoff = today - timedelta(days=2)
    week = [cutoff - timedelta(days=offset) for offset in range(6, -1, -1)]
    month_start = cutoff.replace(day=1)
    month = [month_start + timedelta(days=i) for i in range((cutoff - month_start).days + 1)]

    def total(days):
        if not days or any(day not in readings for day in days):
            return None
        return round(sum(readings[day] for day in days), 3)

    week_liters = total(week)
    month_liters = total(month)
    return {
        "consumption_7d_liters": week_liters,
        "consumption_month_liters": month_liters,
        "average_daily_liters": round(week_liters / 7, 3) if week_liters is not None else None,
        "estimated_month_cost_eur": round(month_liters / 1000 * price_per_m3, 2) if month_liters is not None and price_per_m3 > 0 else None,
        "consumption_period_end": cutoff.isoformat(),
        "consumption_month_start": month_start.isoformat(),
    }
