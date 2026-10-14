"""Deterministic note gate for candidate route-weeks.

Retrieval proposes notes. This module alone decides whether a proposal can
justify a cost increase.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from notes_retrieval import retrieve

ALL_ROUTES = "All Routes"
RAISES_COST = "raises_cost"


@dataclass(frozen=True)
class Verdict:
    flagged: str
    matched_note_id: str | None


def _as_date(value: date | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _week_overlaps_note(week_of: date, note: dict[str, str]) -> bool:
    week_end = week_of + timedelta(days=6)
    note_start = date.fromisoformat(note["window_start"])
    note_end = date.fromisoformat(note["window_end"])
    return note_start <= week_end and note_end >= week_of


def matched_note(
    route: str, week_of: date | str, proposed_notes: list[dict[str, str]]
) -> dict[str, str] | None:
    """Return the best valid proposal, or None when every gate rejects it."""
    week_start = _as_date(week_of)
    qualifying_notes = [
        note
        for note in proposed_notes
        if note["effect"] == RAISES_COST
        and note["applies_to"] in {route, ALL_ROUTES}
        and _week_overlaps_note(week_start, note)
    ]
    if not qualifying_notes:
        return None

    return min(
        qualifying_notes,
        key=lambda note: (
            note["applies_to"] == ALL_ROUTES,
            note["note_id"],
        ),
    )


def determine_verdict(route: str, week_of: date | str) -> Verdict:
    """Retrieve proposals, apply the code gate, and return the verdict."""
    match = matched_note(route, week_of, retrieve(route, week_of))
    if match is None:
        return Verdict(flagged="Yes", matched_note_id=None)
    return Verdict(flagged="No (justified)", matched_note_id=match["note_id"])
