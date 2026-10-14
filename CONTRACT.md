# Output contract

The pipeline writes `outputs/output.csv` with exactly this header, in this
order:

```text
route,week_of,cost_per_tonne_km,vs_own_history,vs_similar_routes,flagged,matched_note_id,reason
```

The canonical machine-readable definition is `config.OUTPUT_COLUMNS`.
