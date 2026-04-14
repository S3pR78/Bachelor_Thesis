def build_raw_result_entry(
    benchmark_entry_id: str,
    question: str,
    gold_query: str | None,
) -> dict:
    return {
        "id": benchmark_entry_id,
        "question": question,
        "gold_query": gold_query,
    }