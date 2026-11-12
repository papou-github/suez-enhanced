"""Dated per-m3 prices. All amounts are variable consumption charges only."""
from bisect import bisect_right
from datetime import date
from math import isfinite


def parse_tariffs(text: str) -> tuple[tuple[date, float], ...]:
    """One YYYY-MM-DD;price per line. Comma decimals accepted."""
    if not isinstance(text, str):
        raise ValueError("Tariff history must be text")
    entries = {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(";")
        if len(parts) != 2:
            raise ValueError(f"Line {number}: expected YYYY-MM-DD;price")
        try:
            day = date.fromisoformat(parts[0].strip())
            amount = float(parts[1].strip().replace(",", "."))
        except (ValueError, OverflowError) as exc:
            raise ValueError(f"Line {number}: invalid date or price") from exc
        if not isfinite(amount) or not 0 <= amount <= 100:
            raise ValueError(f"Line {number}: price must be between 0 and 100")
        if day in entries:
            raise ValueError(f"Line {number}: duplicate effective date")
        entries[day] = amount
    return tuple(sorted(entries.items()))


class TariffSchedule:
    """Use dated prices, falling back to legacy flat price before first change."""

    def __init__(self, fallback: float, history: str = ""):
        self.fallback = float(fallback)
        if not isfinite(self.fallback) or not 0 <= self.fallback <= 100:
            raise ValueError("Invalid fallback price")
        self.entries = parse_tariffs(history)
        self.dates = tuple(day for day, _ in self.entries)
        self.prices = tuple(price for _, price in self.entries)

    def price(self, day: date) -> float:
        position = bisect_right(self.dates, day) - 1
        return self.prices[position] if position >= 0 else self.fallback

    def cost(self, daily_liters: dict[date, float]) -> float:
        return sum(liters / 1000 * self.price(day)
                   for day, liters in daily_liters.items())

    def __eq__(self, other):
        return (isinstance(other, TariffSchedule)
                and self.fallback == other.fallback and self.entries == other.entries)
