import pytest

from notes_retrieval import load_structured_notes
from verdicts import determine_verdict, matched_note


@pytest.mark.parametrize(
    ("route", "week_of", "flagged", "matched_note_id"),
    [
        ("Delhi-Jaipur", "2024-11-11", "Yes", None),
        ("Ahmedabad-Mumbai", "2025-01-20", "No (justified)", "N002"),
        ("Chennai-Bangalore", "2025-02-24", "No (justified)", "N001"),
        ("Chennai-Bangalore", "2025-03-03", "No (justified)", "N001"),
        ("Chennai-Bangalore", "2025-03-10", "Yes", None),
        ("Chennai-Bangalore", "2025-03-17", "Yes", None),
    ],
)
def test_required_verdicts(
    route: str, week_of: str, flagged: str, matched_note_id: str | None
) -> None:
    verdict = determine_verdict(route, week_of)

    assert verdict.flagged == flagged
    assert verdict.matched_note_id == matched_note_id


def test_notes_n004_to_n010_never_justify_a_cost_rise() -> None:
    notes = load_structured_notes()
    non_rise_notes = [note for note in notes if note["note_id"] >= "N004"]

    for note in non_rise_notes:
        route = (
            "Delhi-Jaipur" if note["applies_to"] == "All Routes" else note["applies_to"]
        )
        assert matched_note(route, note["window_start"], [note]) is None


def test_wrong_route_or_window_rejects_a_cost_rise_note() -> None:
    flood_note = next(
        note for note in load_structured_notes() if note["note_id"] == "N001"
    )

    assert matched_note("Delhi-Jaipur", "2025-02-24", [flood_note]) is None
    assert matched_note("Chennai-Bangalore", "2025-03-10", [flood_note]) is None


def test_route_specific_note_beats_all_routes_note() -> None:
    proposals = [
        {
            "note_id": "N003",
            "applies_to": "All Routes",
            "window_start": "2025-05-05",
            "window_end": "2025-05-11",
            "effect": "raises_cost",
            "note": "Nationwide increase.",
        },
        {
            "note_id": "N011",
            "applies_to": "Delhi-Jaipur",
            "window_start": "2025-05-05",
            "window_end": "2025-05-11",
            "effect": "raises_cost",
            "note": "Route-specific increase.",
        },
    ]

    match = matched_note("Delhi-Jaipur", "2025-05-05", proposals)

    assert match is not None
    assert match["note_id"] == "N011"


def test_lowest_note_id_breaks_a_same_scope_tie() -> None:
    proposals = [
        {
            "note_id": "N012",
            "applies_to": "Delhi-Jaipur",
            "window_start": "2025-05-05",
            "window_end": "2025-05-11",
            "effect": "raises_cost",
            "note": "Later note.",
        },
        {
            "note_id": "N011",
            "applies_to": "Delhi-Jaipur",
            "window_start": "2025-05-05",
            "window_end": "2025-05-11",
            "effect": "raises_cost",
            "note": "Earlier note.",
        },
    ]

    match = matched_note("Delhi-Jaipur", "2025-05-05", proposals)

    assert match is not None
    assert match["note_id"] == "N011"
