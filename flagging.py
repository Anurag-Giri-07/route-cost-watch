"""Identify weekly route costs that require an explanation review."""

from __future__ import annotations

import pandas as pd

from baselines import calculate_baselines
from config import OWN_HISTORY_PERCENT_THRESHOLD, SIMILAR_ROUTES_PERCENT_THRESHOLD
from weekly_metrics import load_weekly_metrics


def flag_candidates(metrics_with_baselines: pd.DataFrame) -> pd.DataFrame:
    """Mark rows with a positive own-history rise and an unusual comparison."""
    metrics = metrics_with_baselines.copy()
    own_rise = metrics["vs_own_history_pct"] > 0
    unusual_own_history = (
        metrics["vs_own_history_pct"] >= OWN_HISTORY_PERCENT_THRESHOLD
    )
    unusual_similar_routes = (
        metrics["vs_similar_routes_pct"] >= SIMILAR_ROUTES_PERCENT_THRESHOLD
    )
    metrics["is_candidate"] = (
        own_rise & (unusual_own_history | unusual_similar_routes)
    ).fillna(False)
    return metrics


def candidate_counts_by_route(flagged_metrics: pd.DataFrame) -> pd.DataFrame:
    """Return candidate totals for each route in a stable display order."""
    return (
        flagged_metrics.groupby("route", as_index=False)["is_candidate"]
        .sum()
        .rename(columns={"is_candidate": "candidate_count"})
        .sort_values("route", ignore_index=True)
    )


def main() -> None:
    weekly_metrics = load_weekly_metrics()
    metrics_with_baselines = calculate_baselines(weekly_metrics)
    flagged_metrics = flag_candidates(metrics_with_baselines)
    print(candidate_counts_by_route(flagged_metrics).to_string(index=False))


if __name__ == "__main__":
    main()
