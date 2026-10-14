import csv

from config import OUTPUT_COLUMNS, SAMPLE_OUTPUT_PATH


def test_output_columns_match_sample_contract() -> None:
    with SAMPLE_OUTPUT_PATH.open(newline="", encoding="utf-8") as sample_file:
        sample_header = next(csv.reader(sample_file))

    assert OUTPUT_COLUMNS == sample_header
