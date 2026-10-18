# SUEZ Enhanced — Historical statistics continuity

## Existing Home Assistant installation

The existing Energy dashboard uses:

- Statistic ID: `suez_water:3197811457_water_consumption_statistics`
- Source: `suez_water`
- Unit: `L`
- `has_sum=1`
- First row: 2024-10-06 22:00 UTC, state=197, sum=197
- Last row: 2026-10-16 22:00 UTC, state=0, sum=190174
- 741 rows, one per day (recorded at the start of the next local day)
- SUEZ Enhanced meter index: separate entity in m³
- ESP32CAM112 rainwater: separate water source; never merge

## Rules before implementing an automatic writer

1. Do not change the existing statistic ID or convert the historical L values into m³.
2. Do not add the meter-index sensor as a second Energy water source.
3. Use the Home Assistant recorder external-statistics API; never edit the live recorder SQLite database.
4. Read existing last row and sum, skip every date already stored, and import only complete, validated daily values.
5. Keep timestamps aligned to the existing daily series and its Europe/Paris calendar convention, including DST.
6. Preserve cumulative `sum` across imports. For each new day, add its `volume` (litres) to the previous `sum`.
7. Check whether HA permits a `suez_enhanced` integration to append to an existing external-statistic source named `suez_water`. Do not assume source ownership is transferable.
8. Check `state` and `sum` semantics, unit_class and mean_type for HA 2026.10/2026.11 compatibility.
9. Perform a dry run and take a Home Assistant backup before enabling writes.
10. If daily telemetry is missing or delayed, do not invent zero usage; do not advance the import cursor.

## Read-only inspection

Run in the Home Assistant terminal:

```bash
python3 - <<'PY'
import sqlite3
from datetime import datetime, timezone
sid = "suez_water:3197811457_water_consumption_statistics"
con = sqlite3.connect("file:/config/home-assistant_v2.db?mode=ro", uri=True)
rows = con.execute("""
SELECT s.start_ts, s.state, s.sum
FROM statistics s JOIN statistics_meta m ON m.id=s.metadata_id
WHERE m.statistic_id=? ORDER BY s.start_ts DESC LIMIT 15
""", (sid,)).fetchall()
for ts, state, total in reversed(rows):
    print(datetime.fromtimestamp(ts, timezone.utc).isoformat(), state, total)
con.close()
PY
```

This inspection is safe; no statistics are written.

## Official Home Assistant APIs

- https://developers.home-assistant.io/blog/2025/10/16/recorder-statistics-api-changes/
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/recorder/statistics.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/recorder/websocket_api.py
