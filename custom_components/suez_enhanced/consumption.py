"""Pure, read-only consumption summaries from confirmed SUEZ daily readings."""
from __future__ import annotations

from datetime import date, timedelta
from math import isfinite

from .history import daily_readings
from .tariffs import TariffSchedule


def consumption_summary(measures: list, today: date, price_per_m3: float) -> dict:
    """Return None for incomplete periods, never interpret missing days as zero."""
    tariff = price_per_m3 if isinstance(price_per_m3, TariffSchedule) else TariffSchedule(price_per_m3)
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
    year_start = cutoff.replace(month=1, day=1)
    year_days = [year_start + timedelta(days=i) for i in range((cutoff - year_start).days + 1)]
    year_liters = total(year_days)
    yesterday_liters = readings.get(today - timedelta(days=1))
    # SUEZ data is commonly delayed by two days. Do not silently substitute
    # the last confirmed day for yesterday.
    def period_cost(days):
        if any(day not in readings for day in days):
            return None
        if not any(tariff.price(day) > 0 for day in days):
            return None
        return round(tariff.cost({day: readings[day] for day in days}), 2)

    yesterday_cost = (round(yesterday_liters / 1000 * tariff.price(today - timedelta(days=1)), 2)
                      if yesterday_liters is not None and tariff.price(today - timedelta(days=1)) > 0 else None)
    week_cost = period_cost(week)
    # Annual projection uses the tariff effective on the latest eligible day.
    annual_projection = (round(week_liters / 7 * 365 / 1000 * tariff.price(cutoff), 2)
                         if week_liters is not None and tariff.price(cutoff) > 0 else None)

    return {
        "consumption_7d_liters": week_liters,
        "consumption_month_liters": month_liters,
        "average_daily_liters": round(week_liters / 7, 3) if week_liters is not None else None,
        "estimated_yesterday_cost_eur": yesterday_cost,
        "estimated_7d_cost_eur": week_cost,
        "estimated_month_cost_eur": period_cost(month),
        "estimated_year_to_date_cost_eur": period_cost(year_days),
        "estimated_annual_cost_eur": annual_projection,
        "consumption_period_end": cutoff.isoformat(),
        "consumption_month_start": month_start.isoformat(),
        "consumption_year_start": year_start.isoformat(),
    }
