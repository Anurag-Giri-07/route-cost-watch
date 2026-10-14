import pandas as pd
import pytest

from baselines import calculate_baselines
from flagging import candidate_counts_by_route, flag_candidates
from weekly_metrics import load_weekly_metrics


@pytest.fixture(scope="module")
def flagged_metrics() -> pd.DataFrame:
    return flag_candidates(calculate_baselines(load_weekly_metrics()))


@pytest.mark.parametrize(
    ("route", "week_of"),
    [
        ("Delhi-Jaipur", "2024-11-11"),
        ("Ahmedabad-Mumbai", "2025-01-20"),
        ("Mumbai-Pune", "2025-09-15"),
    ],
)
def test_sample_rows_are_candidates(
    flagged_metrics: pd.DataFrame, route: str, week_of: str
) -> None:
    row = flagged_metrics.loc[
        (flagged_metrics["route"] == route)
        & (flagged_metrics["week_of"] == pd.Timestamp(week_of))
    ].iloc[0]

    assert bool(row["is_candidate"])


@pytest.mark.parametrize(
    ("own_pct", "peer_pct", "expected_candidate"),
    [
        (10.0, 0.0, True),
        (0.0, 25.0, False),
        (9.9, 20.0, True),
        (9.9, 19.9, False),
    ],
)
def test_candidate_rule_boundaries(
    own_pct: float, peer_pct: float, expected_candidate: bool
) -> None:
    metrics = pd.DataFrame(
        {
            "route": ["Delhi-Jaipur"],
            "vs_own_history_pct": [own_pct],
            "vs_similar_routes_pct": [peer_pct],
        }
    )

    result = flag_candidates(metrics)

    assert bool(result.loc[0, "is_candidate"]) is expected_candidate


def test_candidate_counts_are_grouped_by_route() -> None:
    flagged_metrics = pd.DataFrame(
        {
            "route": ["Mumbai-Pune", "Delhi-Jaipur", "Mumbai-Pune"],
            "is_candidate": [True, True, False],
        }
    )

    counts = candidate_counts_by_route(flagged_metrics)

    assert counts.to_dict("records") == [
        {"route": "Delhi-Jaipur", "candidate_count": 1},
        {"route": "Mumbai-Pune", "candidate_count": 1},
    ]
