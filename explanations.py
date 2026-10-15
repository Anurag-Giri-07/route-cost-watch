"""Grounded explanation generation for already-decided verdicts."""

from __future__ import annotations

import re
from typing import Mapping

from llm_wrapper import LLMWrapper, create_default_wrapper
from notes_retrieval import load_structured_notes
from verdicts import Verdict

UNEXPLAINED_REASON = (
    "No matching note found for this route or date range. Cost rise looks "
    "unexplained and worth a human review."
)
NOTE_ID_PATTERN = re.compile(r"\bN\d{3}\b")
REASON_TRANSLATION = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00a0": " ",
        "\u202f": " ",
        "\u2009": " ",
        "\u200b": " ",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
)


def normalize_reason(text: str) -> str:
    return " ".join(text.translate(REASON_TRANSLATION).split())


def _value(row: Mapping[str, object], field: str) -> str:
    return str(row[field])


def build_justified_prompt(row: Mapping[str, object], note: Mapping[str, str]) -> str:
    """Build a prompt containing only the selected row and its matched note."""
    return f"""Write one or two plain-English sentences explaining this justified cost rise.
State the verdict is justified. Include note ID {note['note_id']} and the exact
dates {note['window_start']} and {note['window_end']}. Do not mention any other
note ID or add facts not present below.

Route-week data:
- route: {_value(row, 'route')}
- week_of: {_value(row, 'week_of')}
- cost_per_tonne_km: {_value(row, 'cost_per_tonne_km')}
- vs_own_history: {_value(row, 'vs_own_history')}
- vs_similar_routes: {_value(row, 'vs_similar_routes')}

Matched note:
- note_id: {note['note_id']}
- applies_to: {note['applies_to']}
- window: {note['window_start']} to {note['window_end']}
- note: {note['note']}"""


def fixed_justified_reason(note: Mapping[str, str]) -> str:
    """Return a grounded fallback when LLM output fails validation."""
    return (
        f"Verdict: justified. Note {note['note_id']} covers "
        f"{note['window_start']} to {note['window_end']} and states: {note['note']}"
    )


def is_valid_justified_reason(reason: str, note: Mapping[str, str]) -> bool:
    """Require the selected note ID and dates, with no unrelated note IDs."""
    normalized_reason = normalize_reason(reason)
    cited_note_ids = set(NOTE_ID_PATTERN.findall(reason))
    return (
        note["note_id"] in cited_note_ids
        and cited_note_ids == {note["note_id"]}
        and note["window_start"] in normalized_reason
        and note["window_end"] in normalized_reason
    )


def generate_reason(
    row: Mapping[str, object],
    verdict: Verdict,
    matched_note: Mapping[str, str] | None,
    llm: LLMWrapper | None,
) -> str:
    """Generate a validated explanation without allowing the LLM to choose verdicts."""
    if verdict.matched_note_id is None:
        return UNEXPLAINED_REASON
    if matched_note is None or matched_note["note_id"] != verdict.matched_note_id:
        raise ValueError("a justified verdict requires its exact matched note")
    if llm is None:
        print(
            "Warning: no Groq LLM wrapper is available (check GROQ_API_KEY); "
            "using a deterministic explanation."
        )
        return fixed_justified_reason(matched_note)

    try:
        reason = normalize_reason(
            llm.complete(
                "justified_explanation", build_justified_prompt(row, matched_note)
            )
        )
    except Exception as error:
        print(
            "Warning: Groq explanation call failed "
            f"({type(error).__name__}); using a deterministic explanation."
        )
        return fixed_justified_reason(matched_note)
    if is_valid_justified_reason(reason, matched_note):
        return reason
    return fixed_justified_reason(matched_note)


def main() -> None:
    """Make one real, cacheable Groq explanation call for manual P6 verification."""
    note = next(note for note in load_structured_notes() if note["note_id"] == "N002")
    row = {
        "route": "Ahmedabad-Mumbai",
        "week_of": "2025-01-20",
        "cost_per_tonne_km": "3.29",
        "vs_own_history": "+29.5% vs this route's past average",
        "vs_similar_routes": "+22.5% vs similar-length routes this week",
    }
    verdict = Verdict(flagged="No (justified)", matched_note_id="N002")
    print(generate_reason(row, verdict, note, create_default_wrapper()))


if __name__ == "__main__":
    main()
