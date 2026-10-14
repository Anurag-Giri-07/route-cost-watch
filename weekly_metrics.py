"""Load shipment data and calculate weekly route cost metrics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import SHIPMENT_COLUMNS, SHIPMENT_RECORDS_PATH


NUMERIC_SHIPMENT_COLUMNS = [
    "quantity_tonnes",
    "distance_km",
    "freight_cost_inr",
]


def load_shipments(path: Path = SHIPMENT_RECORDS_PATH) -> pd.DataFrame:
    """Load shipment records and validate the fields needed by the pipeline."""
    shipments = pd.read_csv(path)

    if list(shipments.columns) != SHIPMENT_COLUMNS:
        raise ValueError("shipment_records.csv has an unexpected header")
    if shipments.empty:
        raise ValueError("shipment_records.csv is empty")
    if shipments.isna().any().any():
        raise ValueError("shipment_records.csv contains missing values")

    for column in NUMERIC_SHIPMENT_COLUMNS:
        shipments[column] = pd.to_numeric(shipments[column], errors="raise")
        if (shipments[column] <= 0).any():
            raise ValueError(f"{column} must contain only positive values")

    shipments["shipment_date"] = pd.to_datetime(
        shipments["shipment_date"], errors="raise"
    )
    return shipments


def calculate_weekly_metrics(shipments: pd.DataFrame) -> pd.DataFrame:
    """Return unrounded weekly cost per tonne-km for every route."""
    records = shipments.copy()
    records["route"] = records["origin"] + "-" + records["destination"]
    records["week_of"] = records["shipment_date"] - pd.to_timedelta(
        records["shipment_date"].dt.weekday, unit="D"
    )
    records["tonne_km"] = records["quantity_tonnes"] * records["distance_km"]

    weekly = (
        records.groupby(["route", "route_type", "week_of"], as_index=False)
        .agg(
            freight_cost_inr=("freight_cost_inr", "sum"),
            tonne_km=("tonne_km", "sum"),
        )
        .sort_values(["route", "week_of"], ignore_index=True)
    )
    weekly["cost_per_tonne_km"] = weekly["freight_cost_inr"] / weekly["tonne_km"]
    return weekly[["route", "route_type", "week_of", "cost_per_tonne_km"]]


def load_weekly_metrics(path: Path = SHIPMENT_RECORDS_PATH) -> pd.DataFrame:
    """Load validated shipments and aggregate them into Monday-start weeks."""
    return calculate_weekly_metrics(load_shipments(path))
