"""Build the final candidate-only output table."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from baselines import calculate_baselines
from config import OUTPUT_COLUMNS, OUTPUT_PATH
from explanations import generate_reason
from flagging import flag_candidates
from llm_wrapper import LLMWrapper, create_default_wrapper
from notes_retrieval import load_structured_notes
from verdicts import Verdict, determine_verdict
from weekly_metrics import load_weekly_metrics


def _percentage(value: float, comparison: str) -> str:
    return f"{value:+.1f}% vs {comparison}"


def format_output_row(
    metric: Mapping[str, object], verdict: Verdict, reason: str
) -> dict[str, str]:
    """Format one already-decided candidate row to the CSV contract."""
    return {
        "route": str(metric["route"]),
        "week_of": pd.Timestamp(metric["week_of"]).strftime("%Y-%m-%d"),
        "cost_per_tonne_km": f"{float(metric['cost_per_tonne_km']):.2f}",
        "vs_own_history": _percentage(
            float(metric["vs_own_history_pct"]), "this route's past average"
        ),
        "vs_similar_routes": _percentage(
            float(metric["vs_similar_routes_pct"]), "similar-length routes this week"
        ),
        "flagged": verdict.flagged,
        "matched_note_id": verdict.matched_note_id or "",
        "reason": reason,
    }


def build_output_rows(llm: LLMWrapper | None = None) -> list[dict[str, str]]:
    """Calculate, flag, decide, explain, and format every candidate route-week."""
    weekly_metrics = load_weekly_metrics()
    metrics_with_baselines = calculate_baselines(weekly_metrics)
    flagged_metrics = flag_candidates(metrics_with_baselines)
    candidates = flagged_metrics.loc[flagged_metrics["is_candidate"]].sort_values(
        ["route", "week_of"]
    )
    notes_by_id = {
        note["note_id"]: note for note in load_structured_notes()
    }
    output_rows = []

    for metric in candidates.to_dict("records"):
        verdict = determine_verdict(metric["route"], metric["week_of"])
        note = notes_by_id.get(verdict.matched_note_id)
        if verdict.matched_note_id and llm is None:
            llm = create_default_wrapper()
        output_row = format_output_row(metric, verdict, reason="")
        output_row["reason"] = generate_reason(output_row, verdict, note, llm)
        output_rows.append(output_row)
    return output_rows


def write_output(
    output_rows: list[dict[str, str]], output_path: Path = OUTPUT_PATH
) -> None:
    """Write the exact output CSV header and rows."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)


def main() -> None:
    output_rows = build_output_rows()
    write_output(output_rows)
    print(f"Wrote {len(output_rows)} candidate rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
