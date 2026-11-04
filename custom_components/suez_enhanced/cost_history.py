"""Build dated chart series from confirmed SUEZ daily readings."""
from datetime import timedelta
from math import isfinite

from .history import daily_readings


def cost_history(measures, today, price_per_m3):
    """Return sparse daily and cumulative series, never filling missing days with zero."""
    if not isfinite(price_per_m3) or price_per_m3 <= 0:
        return {"daily_cost_history": [], "cumulative_cost_history": []}
    cutoff = today - timedelta(days=2)
    start = cutoff.replace(month=1, day=1)
    readings = {
        reading.day: reading.liters
        for reading in daily_readings(measures)
        if start <= reading.day <= cutoff
    }
    daily = []
    cumulative = []
    total_liters = 0.0
    complete = True
    day = start
    while day <= cutoff:
        liters = readings.get(day)
        if liters is None:
            complete = False
        else:
            daily.append([day.isoformat(), round(liters / 1000 * price_per_m3, 2)])
            if complete:
                total_liters += liters
                cumulative.append([day.isoformat(), round(total_liters / 1000 * price_per_m3, 2)])
        day += timedelta(days=1)
    return {"daily_cost_history": daily, "cumulative_cost_history": cumulative}
