import pandas as pd
import pytest

from baselines import calculate_baselines
from weekly_metrics import load_weekly_metrics


@pytest.fixture(scope="module")
def metrics_with_baselines() -> pd.DataFrame:
    return calculate_baselines(load_weekly_metrics())


@pytest.mark.parametrize(
    ("route", "week_of", "expected_own_pct", "expected_peer_pct"),
    [
        ("Delhi-Jaipur", "2024-11-11", 35.5, 21.0),
        ("Ahmedabad-Mumbai", "2025-01-20", 29.5, 22.5),
        ("Mumbai-Pune", "2025-09-15", 9.2, 23.6),
    ],
)
def test_sample_baseline_percentages(
    metrics_with_baselines: pd.DataFrame,
    route: str,
    week_of: str,
    expected_own_pct: float,
    expected_peer_pct: float,
) -> None:
    row = metrics_with_baselines.loc[
        (metrics_with_baselines["route"] == route)
        & (metrics_with_baselines["week_of"] == pd.Timestamp(week_of))
    ].iloc[0]

    assert round(row["vs_own_history_pct"], 1) == expected_own_pct
    assert round(row["vs_similar_routes_pct"], 1) == expected_peer_pct


def test_own_history_uses_only_weeks_before_the_current_week() -> None:
    weekly_metrics = pd.DataFrame(
        {
            "route": ["Delhi-Jaipur"] * 4,
            "route_type": ["Medium"] * 4,
            "week_of": pd.to_datetime(
                ["2025-01-06", "2025-01-13", "2025-01-20", "2025-01-27"]
            ),
            "cost_per_tonne_km": [10.0, 20.0, 30.0, 9_999.0],
        }
    )

    result = calculate_baselines(weekly_metrics)
    third_week = result.loc[result["week_of"] == pd.Timestamp("2025-01-20")].iloc[0]

    assert third_week["own_history_baseline"] == 15.0
    assert third_week["prior_weeks_used"] == 2


def test_similar_routes_baseline_excludes_the_current_route() -> None:
    weekly_metrics = pd.DataFrame(
        {
            "route": ["Delhi-Jaipur", "Mumbai-Pune"],
            "route_type": ["Medium", "Medium"],
            "week_of": pd.to_datetime(["2025-01-06", "2025-01-06"]),
            "cost_per_tonne_km": [10.0, 20.0],
        }
    )

    result = calculate_baselines(weekly_metrics)
    delhi = result.loc[result["route"] == "Delhi-Jaipur"].iloc[0]

    assert delhi["similar_routes_baseline"] == 20.0
    assert delhi["vs_similar_routes_pct"] == -50.0
