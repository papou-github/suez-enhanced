# ApexCharts — SUEZ water costs (v0.6.0)

The `Estimated year-to-date cost` sensor exposes two attributes:
- `daily_cost_history`: `[["YYYY-MM-DD", euros], ...]` for confirmed daily readings.
- `cumulative_cost_history`: `[["YYYY-MM-DD", euros], ...]` for the complete uninterrupted part of the year.

Missing days are omitted, never converted to zero. A genuine zero-liter day is included.
The cumulative series stops at the first missing day rather than displaying a misleading total.
Readings have a two-day safety cutoff. Values are estimates based on the current €/m³ setting, not invoices.

## Lovelace card (ApexCharts Card via HACS)

Replace the entity ID if your meter is different:

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: "SUEZ Jardin - Historique des coûts"
  show_states: false
graph_span: 365d
span:
  end: day
yaxis:
  - id: cumulative
    decimals: 0
    min: 0
    apex_config:
      title:
        text: "Cumul (€)"
  - id: daily
    opposite: true
    decimals: 2
    min: 0
    apex_config:
      title:
        text: "Quotidien (€)"
series:
  - entity: sensor.jardin_suez_3197811457_estimated_year_to_date_cost
    name: Cumul annuel
    type: line
    yaxis_id: cumulative
    color: "#2196F3"
    stroke_width: 3
    data_generator: |
      return (entity.attributes.cumulative_cost_history || [])
        .map(([day, cost]) => [new Date(day + "T12:00:00").getTime(), cost]);
  - entity: sensor.jardin_suez_3197811457_estimated_year_to_date_cost
    name: Coût journalier
    type: column
    yaxis_id: daily
    color: "#4CAF50"
    data_generator: |
      return (entity.attributes.daily_cost_history || [])
        .map(([day, cost]) => [new Date(day + "T12:00:00").getTime(), cost]);
```

The chart derives its points from the current sensor attributes, not from historical
Recorder states. The current year is shown; for a shorter view change `graph_span`
(e.g. `30d` or `90d`). Reload the dashboard after upgrading.
