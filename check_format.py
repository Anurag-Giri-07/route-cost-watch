"""Validate that output.csv matches the required CSV contract."""

from __future__ import annotations

import csv
import re
import sys
from datetime import date
from pathlib import Path

from config import OUTPUT_COLUMNS, OUTPUT_PATH, SAMPLE_OUTPUT_PATH

COST_PATTERN = re.compile(r"^\d+\.\d{2}$")
OWN_HISTORY_PATTERN = re.compile(
    r"^[+-]\d+\.\d% vs this route's past average$"
)
SIMILAR_ROUTES_PATTERN = re.compile(
    r"^[+-]\d+\.\d% vs similar-length routes this week$"
)
NOTE_ID_PATTERN = re.compile(r"^N\d{3}$")


def validate_output(path: Path = OUTPUT_PATH) -> int:
    """Validate headers and value patterns, returning the row count."""
    with SAMPLE_OUTPUT_PATH.open(newline="", encoding="utf-8") as sample_file:
        sample_header = next(csv.reader(sample_file))
    with path.open(newline="", encoding="utf-8") as output_file:
        reader = csv.DictReader(output_file)
        if reader.fieldnames != sample_header or reader.fieldnames != OUTPUT_COLUMNS:
            raise ValueError("output header does not match the required contract")
        rows = list(reader)

    for row_number, row in enumerate(rows, start=2):
        _validate_row(row_number, row)
    return len(rows)


def _validate_row(row_number: int, row: dict[str, str]) -> None:
    if not row["route"] or "-" not in row["route"]:
        raise ValueError(f"row {row_number}: invalid route")
    try:
        date.fromisoformat(row["week_of"])
    except ValueError as error:
        raise ValueError(f"row {row_number}: invalid week_of") from error
    if not COST_PATTERN.fullmatch(row["cost_per_tonne_km"]):
        raise ValueError(f"row {row_number}: invalid cost_per_tonne_km")
    if not OWN_HISTORY_PATTERN.fullmatch(row["vs_own_history"]):
        raise ValueError(f"row {row_number}: invalid vs_own_history")
    if not SIMILAR_ROUTES_PATTERN.fullmatch(row["vs_similar_routes"]):
        raise ValueError(f"row {row_number}: invalid vs_similar_routes")
    if row["flagged"] == "Yes":
        if row["matched_note_id"]:
            raise ValueError(f"row {row_number}: unexplained row has a note ID")
    elif row["flagged"] == "No (justified)":
        note_id = row["matched_note_id"]
        if not NOTE_ID_PATTERN.fullmatch(note_id) or note_id not in row["reason"]:
            raise ValueError(f"row {row_number}: justified row lacks its note ID")
    else:
        raise ValueError(f"row {row_number}: invalid flagged value")
    if not row["reason"]:
        raise ValueError(f"row {row_number}: missing reason")


if __name__ == "__main__":
    try:
        row_count = validate_output()
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        sys.exit(1)
    print(f"PASS: {OUTPUT_PATH} matches the output contract ({row_count} rows)")
