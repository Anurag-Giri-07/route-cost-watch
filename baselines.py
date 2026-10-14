"""Calculate historical and comparable-route baselines for weekly metrics."""

from __future__ import annotations

import pandas as pd

from config import TRAILING_HISTORY_WEEKS


def calculate_baselines(weekly_metrics: pd.DataFrame) -> pd.DataFrame:
    """Add unrounded, no-look-ahead baseline and percentage columns."""
    metrics = weekly_metrics.copy().sort_values(
        ["route", "week_of"], ignore_index=True
    )
    costs = metrics["cost_per_tonne_km"]

    metrics["own_history_baseline"] = metrics.groupby("route")[
        "cost_per_tonne_km"
    ].transform(
        lambda route_costs: route_costs.shift(1).rolling(
            TRAILING_HISTORY_WEEKS, min_periods=1
        ).mean()
    )
    metrics["prior_weeks_used"] = metrics.groupby("route").cumcount().clip(
        upper=TRAILING_HISTORY_WEEKS
    )

    peer_groups = metrics.groupby(["route_type", "week_of"])["cost_per_tonne_km"]
    peer_total = peer_groups.transform("sum")
    peer_count = peer_groups.transform("count")
    metrics["similar_routes_baseline"] = (peer_total - costs) / (peer_count - 1)
    metrics.loc[peer_count <= 1, "similar_routes_baseline"] = pd.NA

    metrics["vs_own_history_pct"] = (
        costs / metrics["own_history_baseline"] - 1
    ) * 100
    metrics["vs_similar_routes_pct"] = (
        costs / metrics["similar_routes_baseline"] - 1
    ) * 100
    return metrics
