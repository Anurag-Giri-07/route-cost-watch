from reproducibility import comparable_rows, runs_are_identical


def sample_rows(note_id: str = "N002") -> list[dict[str, str]]:
    return [
        {
            "route": "Ahmedabad-Mumbai",
            "week_of": "2025-01-20",
            "cost_per_tonne_km": "3.29",
            "vs_own_history": "+29.5% vs this route's past average",
            "vs_similar_routes": "+22.5% vs similar-length routes this week",
            "flagged": "No (justified)",
            "matched_note_id": note_id,
            "reason": "A reason can differ without changing the key comparison.",
        }
    ]


def test_reproducibility_comparison_ignores_reason_text() -> None:
    first_run = sample_rows()
    second_run = sample_rows()
    second_run[0]["reason"] = "Different explanation wording."

    assert comparable_rows(first_run) == comparable_rows(second_run)
    assert runs_are_identical([first_run, second_run, sample_rows()])


def test_reproducibility_comparison_detects_a_changed_verdict() -> None:
    changed_run = sample_rows()
    changed_run[0]["flagged"] = "Yes"
    changed_run[0]["matched_note_id"] = ""

    assert not runs_are_identical([sample_rows(), changed_run, sample_rows()])
