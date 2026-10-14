"""Central configuration for the route cost watch pipeline."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

SHIPMENT_RECORDS_PATH = DATA_DIR / "shipment_records.csv"
CONTEXT_NOTES_PATH = DATA_DIR / "context_notes.csv"
SAMPLE_OUTPUT_PATH = DATA_DIR / "sample_output_format_v2.csv"
OUTPUT_PATH = OUTPUT_DIR / "output.csv"
EVAL_LABELS_PATH = PROJECT_ROOT / "eval_labels.csv"

TRAILING_HISTORY_WEEKS = 8
OWN_HISTORY_PERCENT_THRESHOLD = 10
SIMILAR_ROUTES_PERCENT_THRESHOLD = 20
OPEN_ENDED_NOTE_WEEKS = 1
RETRIEVAL_TOP_K = 3
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_STORE_DIR = PROJECT_ROOT / "vector_store"
NOTES_STRUCTURED_PATH = PROJECT_ROOT / "notes_structured.json"
LLM_CACHE_DIR = PROJECT_ROOT / "llm_cache"
LLM_USAGE_LOG_PATH = OUTPUT_DIR / "llm_usage.csv"
LLM_BASE_URL = "https://api.groq.com/openai/v1"
LLM_API_KEY_ENV_VAR = "GROQ_API_KEY"
LLM_DEFAULT_MODEL = "openai/gpt-oss-120b"
LLM_TEMPERATURE = 0
LLM_MAX_OUTPUT_TOKENS = 600
PUBLISHED_MODEL_PRICES_PER_MILLION = {
    "openai/gpt-oss-120b": {"input": 0.15, "output": 0.60},
}
REPRO_CHECK_PATH = PROJECT_ROOT / "repro_check.md"
P9_TOKEN_COST_LOG_PATH = OUTPUT_DIR / "p9_token_cost_log.csv"

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

SHIPMENT_COLUMNS = [
    "shipment_id",
    "origin",
    "destination",
    "route_type",
    "material",
    "quantity_tonnes",
    "distance_km",
    "freight_cost_inr",
    "shipment_date",
    "transporter",
]
