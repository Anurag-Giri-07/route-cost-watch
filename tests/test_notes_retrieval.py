from notes_retrieval import load_structured_notes, retrieve


def test_structured_notes_have_all_ten_source_notes() -> None:
    notes = load_structured_notes()

    assert [note["note_id"] for note in notes] == [
        f"N{number:03d}" for number in range(1, 11)
    ]


def test_retrieve_surfaces_chennai_flood_note() -> None:
    notes = retrieve("Chennai-Bangalore", "2025-02-24")

    assert "N001" in [note["note_id"] for note in notes]


def test_retrieve_surfaces_ahmedabad_festival_note() -> None:
    notes = retrieve("Ahmedabad-Mumbai", "2025-01-20")

    assert "N002" in [note["note_id"] for note in notes]
