import csv

from evaluate import grounding_check_errors, score_labels
from verdicts import Verdict


def test_score_labels_counts_false_justified_separately() -> None:
    labels = [
        {
            "route": "Delhi-Jaipur",
            "week_of": "2024-11-11",
            "expected_flagged": "Yes",
            "expected_note_id": "",
        },
        {
            "route": "Ahmedabad-Mumbai",
            "week_of": "2025-01-20",
            "expected_flagged": "No (justified)",
            "expected_note_id": "N002",
        },
    ]
    predictions = {
        ("Delhi-Jaipur", "2024-11-11"): Verdict("No (justified)", "N003"),
        ("Ahmedabad-Mumbai", "2025-01-20"): Verdict("No (justified)", "N002"),
    }

    score = score_labels(labels, predictions)

    assert score.correct_verdicts == 1
    assert score.correct_note_ids == 1
    assert score.false_justified == 1


def test_grounding_check_rejects_a_wrong_route_note(tmp_path) -> None:
    output_path = tmp_path / "output.csv"
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=["route", "week_of", "flagged", "matched_note_id", "reason"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "route": "Delhi-Jaipur",
                "week_of": "2025-02-24",
                "flagged": "No (justified)",
                "matched_note_id": "N001",
                "reason": "Note N001 covers 2025-02-24 to 2025-03-08.",
            }
        )

    errors = grounding_check_errors(output_path)

    assert errors == ["row 2: note fails verdict gate"]
