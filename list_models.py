"""Print model IDs that the configured API key can use."""

from llm_wrapper import list_configured_model_ids


def main() -> None:
    for model_id in list_configured_model_ids():
        print(model_id)


if __name__ == "__main__":
    main()
