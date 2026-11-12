"""Identify a provisional zero in the most recent SUEZ daily telemetry."""
from datetime import date, datetime
from math import isfinite


def confirmed_yesterday(measures, target_day: date):
    """Return yesterday's reading only if it is not an unindexed zero.

    SUEZ sometimes sends volume=0, index=None before publishing the actual
    daily usage. A true zero with a valid meter index remains legitimate.
    """
    for measure in measures:
        day = measure.date
        if isinstance(day, datetime):
            day = day.date()
        if day != target_day:
            continue
        volume = measure.volume
        if not isinstance(volume, (int, float)) or not isfinite(volume) or volume < 0:
            return None
        if volume == 0 and measure.index is None:
            return None
        return measure
    return None


def without_provisional_yesterday(measures, target_day: date):
    """Exclude only the unconfirmed current-yesterday zero from summaries."""
    if confirmed_yesterday(measures, target_day) is not None:
        return measures
    return [m for m in measures if (
        (m.date.date() if isinstance(m.date, datetime) else m.date) != target_day
    )]
