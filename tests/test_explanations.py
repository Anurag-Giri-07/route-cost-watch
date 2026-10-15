import csv

from explanations import (
    UNEXPLAINED_REASON,
    build_justified_prompt,
    generate_reason,
    is_valid_justified_reason,
    normalize_reason,
)
from llm_wrapper import LLMResponse, LLMWrapper
from verdicts import Verdict


class FakeClient:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.calls = 0

    def complete(self, model: str, prompt: str) -> LLMResponse:
        self.calls += 1
        return LLMResponse(self.response_text, input_tokens=12, output_tokens=8)


def sample_row() -> dict[str, str]:
    return {
        "route": "Ahmedabad-Mumbai",
        "week_of": "2025-01-20",
        "cost_per_tonne_km": "3.29",
        "vs_own_history": "+29.5% vs this route's past average",
        "vs_similar_routes": "+22.5% vs similar-length routes this week",
    }


def sample_note() -> dict[str, str]:
    return {
        "note_id": "N002",
        "applies_to": "Ahmedabad-Mumbai",
        "window_start": "2025-01-20",
        "window_end": "2025-01-26",
        "effect": "raises_cost",
        "note": "Festival demand caused a temporary surcharge.",
    }


def test_unexplained_reason_is_fixed_without_an_llm_call(tmp_path) -> None:
    client = FakeClient("unused")
    llm = LLMWrapper(client, "test-model", tmp_path / "cache", tmp_path / "usage.csv")

    reason = generate_reason(sample_row(), Verdict("Yes", None), None, llm)

    assert reason == UNEXPLAINED_REASON
    assert client.calls == 0


def test_justified_reason_uses_only_the_matched_note_and_validates(tmp_path) -> None:
    note = sample_note()
    response = "Verdict: justified. Note N002 covers 2025-01-20 to 2025-01-26."
    client = FakeClient(response)
    llm = LLMWrapper(client, "test-model", tmp_path / "cache", tmp_path / "usage.csv")

    reason = generate_reason(
        sample_row(), Verdict("No (justified)", "N002"), note, llm
    )

    assert reason == response
    assert is_valid_justified_reason(reason, note)
    prompt = build_justified_prompt(sample_row(), note)
    assert "N002" in prompt
    assert "N001" not in prompt


def test_invalid_llm_reason_uses_grounded_fallback(tmp_path) -> None:
    note = sample_note()
    client = FakeClient("Verdict: justified because of note N001.")
    llm = LLMWrapper(client, "test-model", tmp_path / "cache", tmp_path / "usage.csv")

    reason = generate_reason(
        sample_row(), Verdict("No (justified)", "N002"), note, llm
    )

    assert "N002" in reason
    assert "2025-01-20" in reason
    assert "N001" not in reason


def test_validator_accepts_unicode_hyphens_in_matched_note_dates() -> None:
    note = sample_note()
    reason = "Verdict: justified. Note N002 covers 2025‑01‑20 to 2025‑01‑26."

    assert is_valid_justified_reason(reason, note)


def test_normalize_reason_is_ascii() -> None:
    text = "N002\u202f(2025\u201101\u201120)\u00a0on\u200bthe \u2019x\u2019"

    assert normalize_reason(text) == "N002 (2025-01-20) on the 'x'"


def test_wrapper_caches_and_logs_each_request(tmp_path) -> None:
    client = FakeClient("Cached response")
    usage_log = tmp_path / "usage.csv"
    llm = LLMWrapper(client, "test-model", tmp_path / "cache", usage_log)

    assert llm.complete("test", "same prompt") == "Cached response"
    assert llm.complete("test", "same prompt") == "Cached response"
    assert client.calls == 1

    with usage_log.open(newline="", encoding="utf-8") as log_file:
        log_rows = list(csv.DictReader(log_file))
    assert [row["cache_hit"] for row in log_rows] == ["No", "Yes"]
    assert [row["input_tokens"] for row in log_rows] == ["12", "12"]
