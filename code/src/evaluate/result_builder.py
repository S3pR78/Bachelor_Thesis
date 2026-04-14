def build_raw_result_entry(
    entry_id: str,
    question: str,
    gold_query: str | None,
) -> dict:
    return {
        "id": entry_id,
        "question": question,
        "gold_query": gold_query,
    }