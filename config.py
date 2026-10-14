"""Central configuration for the route cost watch pipeline."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

SHIPMENT_RECORDS_PATH = DATA_DIR / "shipment_records.csv"
CONTEXT_NOTES_PATH = DATA_DIR / "context_notes.csv"
SAMPLE_OUTPUT_PATH = DATA_DIR / "sample_output_format_v2.csv"
OUTPUT_PATH = OUTPUT_DIR / "output.csv"

OUTPUT_COLUMNS = [
    "route",
    "week_of",
    "cost_per_tonne_km",
    "vs_own_history",
    "vs_similar_routes",
    "flagged",
    "matched_note_id",
    "reason",
]
