"""Build dated chart series from confirmed SUEZ daily readings."""
from datetime import timedelta
from math import isfinite

from .history import daily_readings
from .tariffs import TariffSchedule


def cost_history(measures, today, price_per_m3):
    """Return sparse daily and cumulative series, never filling missing days with zero."""
    tariff = price_per_m3 if isinstance(price_per_m3, TariffSchedule) else TariffSchedule(price_per_m3)
    cutoff = today - timedelta(days=2)
    start = cutoff.replace(month=1, day=1)
    readings = {
        reading.day: reading.liters
        for reading in daily_readings(measures)
        if start <= reading.day <= cutoff
    }
    daily = []
    cumulative = []
    total_cost = 0.0
    complete = True
    day = start
    while day <= cutoff:
        liters = readings.get(day)
        if liters is None:
            complete = False
        else:
            daily.append([day.isoformat(), round(liters / 1000 * tariff.price(day), 2)])
            if complete:
                total_cost += liters / 1000 * tariff.price(day)
                cumulative.append([day.isoformat(), round(total_cost, 2)])
        day += timedelta(days=1)
    return {"daily_cost_history": daily, "cumulative_cost_history": cumulative}
