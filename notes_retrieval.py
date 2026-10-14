"""Local embedding retrieval for structured context notes.

Retrieved notes are proposals only. Verdict logic belongs in a later phase.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from config import (
    EMBEDDING_MODEL_NAME,
    NOTES_STRUCTURED_PATH,
    OPEN_ENDED_NOTE_WEEKS,
    RETRIEVAL_TOP_K,
    VECTOR_STORE_DIR,
)

INDEX_PATH = VECTOR_STORE_DIR / "notes_index.npz"
REQUIRED_NOTE_FIELDS = {
    "note_id",
    "applies_to",
    "window_start",
    "window_end",
    "effect",
    "note",
}


def load_structured_notes(path: Path = NOTES_STRUCTURED_PATH) -> list[dict[str, str]]:
    """Load and validate the hand-reviewable note records."""
    with path.open(encoding="utf-8") as note_file:
        notes = json.load(note_file)

    if not isinstance(notes, list) or not notes:
        raise ValueError("notes_structured.json must contain a non-empty list")
    for note in notes:
        if set(note) != REQUIRED_NOTE_FIELDS:
            raise ValueError("structured note has unexpected fields")
        if note["effect"] not in {"raises_cost", "no_cost_effect"}:
            raise ValueError("structured note has an unsupported effect")
        date.fromisoformat(note["window_start"])
        date.fromisoformat(note["window_end"])

    diesel_note = next(note for note in notes if note["note_id"] == "N003")
    diesel_start = date.fromisoformat(diesel_note["window_start"])
    expected_end = diesel_start + timedelta(days=7 * OPEN_ENDED_NOTE_WEEKS - 1)
    if diesel_note["window_end"] != expected_end.isoformat():
        raise ValueError("N003 must use the configured one-week default window")
    return notes


def _note_text(note: dict[str, str]) -> str:
    return (
        f"Route: {note['applies_to']}. "
        f"Window: {note['window_start']} to {note['window_end']}. "
        f"Note: {note['note']}"
    )


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def build_note_index() -> None:
    """Embed structured notes and persist a local vector index."""
    notes = load_structured_notes()
    embeddings = _model().encode(
        [_note_text(note) for note in notes], normalize_embeddings=True
    )
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        INDEX_PATH,
        note_ids=np.array([note["note_id"] for note in notes]),
        embeddings=embeddings,
    )


def _load_index() -> tuple[np.ndarray, np.ndarray]:
    if not INDEX_PATH.exists():
        build_note_index()
    with np.load(INDEX_PATH) as index:
        return index["note_ids"], index["embeddings"]


def retrieve(
    route: str, week_of: date | str, top_k: int = RETRIEVAL_TOP_K
) -> list[dict[str, str]]:
    """Return the most relevant proposed notes for a route and Monday date."""
    if top_k < 1:
        raise ValueError("top_k must be positive")

    notes = load_structured_notes()
    notes_by_id = {note["note_id"]: note for note in notes}
    note_ids, embeddings = _load_index()
    query = f"Shipping cost increase for route {route} during week of {week_of}."
    query_embedding = _model().encode(query, normalize_embeddings=True)
    scores = embeddings @ query_embedding
    result_ids = note_ids[np.argsort(-scores)[:top_k]]
    return [notes_by_id[note_id] for note_id in result_ids]
