"""Run the full output pipeline three times and report deterministic results."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from config import (
    OUTPUT_DIR,
    OUTPUT_PATH,
    P9_TOKEN_COST_LOG_PATH,
    PUBLISHED_MODEL_PRICES_PER_MILLION,
    REPRO_CHECK_PATH,
)
from llm_wrapper import create_default_wrapper
from output_pipeline import build_output_rows, write_output

COMPARISON_COLUMNS = [
    "route",
    "week_of",
    "cost_per_tonne_km",
    "vs_own_history",
    "vs_similar_routes",
    "flagged",
    "matched_note_id",
]


def comparable_rows(rows: list[dict[str, str]]) -> list[tuple[str, ...]]:
    """Select the output values that must be identical across repeat runs."""
    return [tuple(row[column] for column in COMPARISON_COLUMNS) for row in rows]


def runs_are_identical(run_rows: list[list[dict[str, str]]]) -> bool:
    """Check all numeric, verdict, and matched-note values across three runs."""
    first_run = comparable_rows(run_rows[0])
    return all(comparable_rows(rows) == first_run for rows in run_rows[1:])


def write_token_cost_log(usage_log_path: Path, model: str) -> dict[str, str]:
    """Summarize uncached calls from the first full run at published rates."""
    with usage_log_path.open(newline="", encoding="utf-8") as usage_file:
        calls = [row for row in csv.DictReader(usage_file) if row["cache_hit"] == "No"]

    input_tokens = sum(int(row["input_tokens"]) for row in calls)
    output_tokens = sum(int(row["output_tokens"]) for row in calls)
    prices = PUBLISHED_MODEL_PRICES_PER_MILLION[model]
    rough_cost = (
        input_tokens * prices["input"] + output_tokens * prices["output"]
    ) / 1_000_000
    summary = {
        "model": model,
        "uncached_llm_calls": str(len(calls)),
        "input_tokens": str(input_tokens),
        "output_tokens": str(output_tokens),
        "published_rate_estimate_usd": f"{rough_cost:.6f}",
        "actual_cost": "0.00 (Groq free tier)",
    }

    P9_TOKEN_COST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with P9_TOKEN_COST_LOG_PATH.open("w", newline="", encoding="utf-8") as log_file:
        writer = csv.DictWriter(log_file, fieldnames=list(summary))
        writer.writeheader()
        writer.writerow(summary)
    return summary


def write_repro_check(identical: bool, summary: dict[str, str]) -> None:
    """Write the requested concise reproducibility report."""
    status = "PASS" if identical else "FAIL"
    REPRO_CHECK_PATH.write_text(
        "# Reproducibility check\n\n"
        f"- Three full output-pipeline runs: **{status}**\n"
        "- Compared fields: cost values, percentage values, verdicts, and matched note IDs.\n"
        f"- Model: `{summary['model']}`\n"
        f"- Uncached LLM calls in run 1: {summary['uncached_llm_calls']}\n"
        f"- Input tokens: {summary['input_tokens']}\n"
        f"- Output tokens: {summary['output_tokens']}\n"
        f"- Published-rate estimate: ${summary['published_rate_estimate_usd']}\n"
        "- Actual cost: $0.00 (Groq free tier).\n",
        encoding="utf-8",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OUTPUT_DIR, prefix="p9_") as temp_directory:
        temporary_path = Path(temp_directory)
        usage_log_path = temporary_path / "llm_usage.csv"
        llm = create_default_wrapper(
            cache_dir=temporary_path / "cache",
            usage_log_path=usage_log_path,
        )
        run_rows = [build_output_rows(llm) for _ in range(3)]
        summary = write_token_cost_log(usage_log_path, llm.model)

    identical = runs_are_identical(run_rows)
    write_output(run_rows[-1], OUTPUT_PATH)
    write_repro_check(identical, summary)
    if not identical:
        raise SystemExit("FAIL: output values differ across reproducibility runs")

    print("PASS: 3 output runs have identical numeric, verdict, and note fields")
    print(f"Wrote {REPRO_CHECK_PATH}")
    print(f"Wrote {P9_TOKEN_COST_LOG_PATH}")
    print(
        "Token summary: "
        f"{summary['input_tokens']} input, {summary['output_tokens']} output, "
        f"{summary['uncached_llm_calls']} uncached calls"
    )


if __name__ == "__main__":
    main()
