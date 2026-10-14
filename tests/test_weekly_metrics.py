import pandas as pd
import pytest

from weekly_metrics import load_shipments, load_weekly_metrics


@pytest.fixture(scope="module")
def weekly_metrics() -> pd.DataFrame:
    return load_weekly_metrics()


def test_shipment_records_load_and_validate() -> None:
    shipments = load_shipments()

    assert len(shipments) == 2_940
    assert shipments["shipment_date"].dtype.kind == "M"


def test_weekly_metrics_has_expected_route_week_count(
    weekly_metrics: pd.DataFrame,
) -> None:
    assert len(weekly_metrics) == 728


def test_week_of_is_always_a_monday(weekly_metrics: pd.DataFrame) -> None:
    assert weekly_metrics["week_of"].dt.weekday.eq(0).all()


@pytest.mark.parametrize(
    ("route", "week_of", "expected_cost"),
    [
        ("Delhi-Jaipur", "2024-11-11", 4.17),
        ("Ahmedabad-Mumbai", "2025-01-20", 3.29),
        ("Mumbai-Pune", "2025-09-15", 3.98),
    ],
)
def test_sample_weekly_costs(
    weekly_metrics: pd.DataFrame,
    route: str,
    week_of: str,
    expected_cost: float,
) -> None:
    metric = weekly_metrics.loc[
        (weekly_metrics["route"] == route)
        & (weekly_metrics["week_of"] == pd.Timestamp(week_of)),
        "cost_per_tonne_km",
    ].iloc[0]

    assert metric == pytest.approx(expected_cost, abs=0.005)
