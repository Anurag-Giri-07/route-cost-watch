"""Evaluation harness for numeric correctness, verdicts, traps, and grounding."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from baselines import calculate_baselines
from config import EVAL_LABELS_PATH, OUTPUT_PATH
from explanations import is_valid_justified_reason
from notes_retrieval import load_structured_notes
from verdicts import Verdict, determine_verdict, matched_note
from weekly_metrics import load_weekly_metrics

NUMERIC_EXPECTATIONS = [
    ("Delhi-Jaipur", "2024-11-11", 4.17, 35.5, 21.0),
    ("Ahmedabad-Mumbai", "2025-01-20", 3.29, 29.5, 22.5),
    ("Mumbai-Pune", "2025-09-15", 3.98, 9.2, 23.6),
]


@dataclass(frozen=True)
class LabelScore:
    total: int
    correct_verdicts: int
    justified_total: int
    correct_note_ids: int
    false_justified: int


def load_labels(path: Path = EVAL_LABELS_PATH) -> list[dict[str, str]]:
    """Load the small hand-labeled evaluation set."""
    with path.open(newline="", encoding="utf-8") as label_file:
        return list(csv.DictReader(label_file))


def numeric_check_errors() -> list[str]:
    """Return discrepancies for the required cost and baseline examples."""
    metrics = calculate_baselines(load_weekly_metrics())
    errors = []
    for route, week_of, cost, own_pct, peer_pct in NUMERIC_EXPECTATIONS:
        row = metrics.loc[
            (metrics["route"] == route)
            & (metrics["week_of"].dt.strftime("%Y-%m-%d") == week_of)
        ].iloc[0]
        actuals = (
            round(row["cost_per_tonne_km"], 2),
            round(row["vs_own_history_pct"], 1),
            round(row["vs_similar_routes_pct"], 1),
        )
        expected = (cost, own_pct, peer_pct)
        if actuals != expected:
            errors.append(f"{route} {week_of}: expected {expected}, got {actuals}")
    return errors


def score_labels(
    labels: list[dict[str, str]], predictions: dict[tuple[str, str], Verdict]
) -> LabelScore:
    """Score verdicts and note IDs, separating dangerous false justifications."""
    correct_verdicts = 0
    justified_total = 0
    correct_note_ids = 0
    false_justified = 0

    for label in labels:
        prediction = predictions[(label["route"], label["week_of"])]
        if prediction.flagged == label["expected_flagged"]:
            correct_verdicts += 1
        if (
            prediction.flagged == "No (justified)"
            and label["expected_flagged"] == "Yes"
        ):
            false_justified += 1
        if label["expected_flagged"] == "No (justified)":
            justified_total += 1
            if prediction.matched_note_id == label["expected_note_id"]:
                correct_note_ids += 1

    return LabelScore(
        total=len(labels),
        correct_verdicts=correct_verdicts,
        justified_total=justified_total,
        correct_note_ids=correct_note_ids,
        false_justified=false_justified,
    )


def trap_check_errors() -> list[str]:
    """Verify non-rise notes and invalid scope/window matches never justify."""
    notes = load_structured_notes()
    notes_by_id = {note["note_id"]: note for note in notes}
    errors = []

    for note_id in [f"N{number:03d}" for number in range(4, 11)]:
        note = notes_by_id[note_id]
        route = (
            "Delhi-Jaipur"
            if note["applies_to"] == "All Routes"
            else note["applies_to"]
        )
        if matched_note(route, note["window_start"], [note]) is not None:
            errors.append(f"{note_id} incorrectly justified a rise")
    if matched_note("Delhi-Jaipur", "2025-02-24", [notes_by_id["N001"]]):
        errors.append("N001 incorrectly matched a different route")
    if matched_note("Chennai-Bangalore", "2025-03-10", [notes_by_id["N001"]]):
        errors.append("N001 incorrectly matched after its window")
    return errors


def grounding_check_errors(path: Path = OUTPUT_PATH) -> list[str]:
    """Validate every justified output row against its exact structured note."""
    notes_by_id = {note["note_id"]: note for note in load_structured_notes()}
    errors = []
    with path.open(newline="", encoding="utf-8") as output_file:
        for row_number, row in enumerate(csv.DictReader(output_file), start=2):
            if row["flagged"] != "No (justified)":
                continue
            note = notes_by_id.get(row["matched_note_id"])
            if note is None:
                errors.append(f"row {row_number}: unknown note ID")
                continue
            if matched_note(row["route"], row["week_of"], [note]) is None:
                errors.append(f"row {row_number}: note fails verdict gate")
            if not is_valid_justified_reason(row["reason"], note):
                errors.append(f"row {row_number}: reason fails grounding check")
    return errors


def main() -> None:
    numeric_errors = numeric_check_errors()
    labels = load_labels()
    predictions = {
        (label["route"], label["week_of"]): determine_verdict(
            label["route"], label["week_of"]
        )
        for label in labels
    }
    label_score = score_labels(labels, predictions)
    trap_errors = trap_check_errors()
    grounding_errors = grounding_check_errors()

    all_errors = numeric_errors + trap_errors + grounding_errors
    if label_score.false_justified:
        all_errors.append("false-justified count must be zero")
    if all_errors:
        raise SystemExit("FAIL:\n- " + "\n- ".join(all_errors))

    print(
        f"PASS: numeric checks ({len(NUMERIC_EXPECTATIONS)}/{len(NUMERIC_EXPECTATIONS)})"
    )
    print(
        "PASS: hand labels "
        f"verdict accuracy {label_score.correct_verdicts}/{label_score.total}; "
        f"note ID accuracy {label_score.correct_note_ids}/{label_score.justified_total}; "
        f"false justified {label_score.false_justified}"
    )
    print("PASS: trap checks (N004-N010, wrong route, wrong window)")
    print("PASS: grounding check on every justified output row")


if __name__ == "__main__":
    main()
