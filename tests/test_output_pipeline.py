import pandas as pd

from check_format import validate_output
from output_pipeline import build_output_rows, format_output_row, write_output
from verdicts import Verdict


def sample_metric() -> dict[str, object]:
    return {
        "route": "Ahmedabad-Mumbai",
        "week_of": "2025-01-20",
        "cost_per_tonne_km": 3.294,
        "vs_own_history_pct": 29.54,
        "vs_similar_routes_pct": 22.45,
    }


def test_format_output_row_uses_contract_values() -> None:
    row = format_output_row(
        sample_metric(),
        Verdict("No (justified)", "N002"),
        "Verdict: justified. Note N002 covers 2025-01-20 to 2025-01-26.",
    )

    assert list(row) == [
        "route",
        "week_of",
        "cost_per_tonne_km",
        "vs_own_history",
        "vs_similar_routes",
        "flagged",
        "matched_note_id",
        "reason",
    ]
    assert row["cost_per_tonne_km"] == "3.29"
    assert row["vs_own_history"] == "+29.5% vs this route's past average"
    assert row["vs_similar_routes"] == "+22.4% vs similar-length routes this week"


def test_check_format_accepts_a_valid_output_file(tmp_path) -> None:
    output_path = tmp_path / "output.csv"
    row = format_output_row(
        sample_metric(),
        Verdict("Yes", None),
        "No matching note found for this route or date range. Cost rise looks unexplained and worth a human review.",
    )
    write_output([row], output_path)

    assert validate_output(output_path) == 1


def test_build_output_rows_passes_formatted_values_to_explanations(monkeypatch) -> None:
    candidate = {
        **sample_metric(),
        "route_type": "Medium",
        "is_candidate": True,
    }
    monkeypatch.setattr(
        "output_pipeline.load_weekly_metrics", lambda: object()
    )
    monkeypatch.setattr(
        "output_pipeline.calculate_baselines", lambda _: object()
    )
    monkeypatch.setattr(
        "output_pipeline.flag_candidates",
        lambda _: pd.DataFrame([candidate]),
    )
    monkeypatch.setattr(
        "output_pipeline.load_structured_notes",
        lambda: [sample_note()],
    )
    monkeypatch.setattr(
        "output_pipeline.determine_verdict",
        lambda *_: Verdict("No (justified)", "N002"),
    )

    received_rows = []

    def fake_generate_reason(row, *_):
        received_rows.append(row)
        return "Verdict: justified. Note N002 covers 2025-01-20 to 2025-01-26."

    monkeypatch.setattr("output_pipeline.generate_reason", fake_generate_reason)

    output_rows = build_output_rows(llm=object())

    assert output_rows[0]["reason"].startswith("Verdict: justified.")
    assert received_rows[0]["vs_own_history"] == "+29.5% vs this route's past average"


def sample_note() -> dict[str, str]:
    return {
        "note_id": "N002",
        "applies_to": "Ahmedabad-Mumbai",
        "window_start": "2025-01-20",
        "window_end": "2025-01-26",
        "effect": "raises_cost",
        "note": "Festival demand caused a temporary surcharge.",
    }
