from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def load_json_file(path: Path) -> Any:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(path: Path, payload: Any, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {path}. Use --overwrite to replace it."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_list_of_dicts(obj: Any, path: Path) -> list[dict[str, Any]]:
    if not isinstance(obj, list):
        raise ValueError(f"{path} must contain a JSON array.")

    for index, item in enumerate(obj, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Item {index} in {path} is not a JSON object.")

    return obj


def strip_prefixes(query: str) -> str:
    lines = [line.strip() for line in query.splitlines() if line.strip()]
    non_prefix_lines = [line for line in lines if not line.upper().startswith("PREFIX ")]
    return "\n".join(non_prefix_lines).strip()


def detect_query_components(query: str) -> list[str]:
    q = strip_prefixes(query).upper()
    components: list[str] = []

    checks = [
        ("SELECT", "SELECT"),
        ("ASK", "ASK"),
        ("COUNT(", "COUNT"),
        ("FILTER", "FILTER"),
        ("REGEX", "REGEX"),
        ("STR(", "STR"),
        ("ORDER BY", "ORDER_BY"),
        ("GROUP BY", "GROUP_BY"),
        ("HAVING", "HAVING"),
        ("LIMIT", "LIMIT"),
        ("OPTIONAL", "OPTIONAL"),
        ("UNION", "UNION"),
        ("NOT EXISTS", "NOT_EXISTS"),
        ("MIN(", "MIN"),
        ("MAX(", "MAX"),
        ("AVG(", "AVG"),
        ("IF(", "IF"),
        ("BIND(", "BIND"),
    ]

    for needle, label in checks:
        if needle in q:
            components.append(label)

    return components


def count_triple_patterns(query: str) -> int:
    body = strip_prefixes(query)

    # rough but useful approximation:
    # count " .", excluding PREFIX lines already removed
    count = body.count(" .")
    if count == 0:
        # fallback for compact queries
        count = body.count(".")
    return max(1, count)


def infer_query_type(components: list[str], answer_type: str) -> str:
    if answer_type in {"number", "boolean", "list", "mixed"}:
        return "non_factoid"
    if any(c in components for c in {"COUNT", "GROUP_BY", "HAVING", "MIN", "MAX", "AVG"}):
        return "non_factoid"
    return "factoid"


def infer_query_shape(query: str) -> str:
    q = strip_prefixes(query).upper()

    if "UNION" in q:
        return "forest"
    if "OPTIONAL" in q and ("FILTER" in q or "BIND" in q):
        return "tree"

    pattern_count = count_triple_patterns(query)
    if pattern_count <= 2:
        return "edge"
    if pattern_count <= 4:
        return "chain"
    if pattern_count <= 7:
        return "star"
    return "tree"


def infer_special_types(components: list[str], answer_type: str, query: str) -> list[str]:
    q = strip_prefixes(query).upper()
    special: list[str] = []

    if answer_type == "resource":
        special.append("lookup")
    if "COUNT" in components:
        special.append("count")
    if any(c in components for c in {"MIN", "MAX", "AVG", "GROUP_BY", "HAVING"}):
        special.append("aggregation")
    if "ORDER_BY" in components or "LIMIT" in components:
        special.append("ranking")
    if any(word in q for word in ["MIN(", "MAX("]):
        special.append("superlative")
    if "NOT_EXISTS" in components:
        special.append("missing_info")
        special.append("negation")
    if "REGEX" in components or "STR" in components:
        special.append("string_operation")
    if "FILTER" in components and ("P29" in q or "YEAR" in q):
        special.append("temporal")
    if "OPTIONAL" in components and count_triple_patterns(query) >= 5:
        special.append("multi_hop")
    if answer_type == "boolean" or "ASK" in components:
        special.append("boolean")

    # remove duplicates, keep order
    deduped: list[str] = []
    for item in special:
        if item not in deduped:
            deduped.append(item)
    return deduped


def infer_complexity_level(components: list[str], pattern_count: int) -> str:
    score = 0

    score += min(pattern_count, 10)
    score += len(components)

    if any(c in components for c in {"UNION", "GROUP_BY", "HAVING", "NOT_EXISTS", "BIND"}):
        score += 2
    if any(c in components for c in {"MIN", "MAX", "AVG", "COUNT"}):
        score += 1

    if score <= 7:
        return "low"
    if score <= 13:
        return "medium"
    return "high"


def infer_source_dataset(family: str) -> str:
    if family == "nlp4re":
        return "Hybrid_NLP4RE"
    if family == "empirical_research_practice":
        return "Hybrid_Empirical_Research"
    raise ValueError(f"Unknown family: {family}")


def infer_schema_id(source_id: str, family: str) -> str:
    if family == "nlp4re":
        prefix = "nlp4re"
    elif family == "empirical_research_practice":
        prefix = "empirical-research-practice"
    else:
        raise ValueError(f"Unknown family: {family}")

    m = re.search(r"(\d+)$", source_id)
    if not m:
        raise ValueError(f"Could not extract numeric suffix from source_id '{source_id}'")

    numeric = int(m.group(1))
    return f"{prefix}-{numeric:04d}"


def enrich_item(item: dict[str, Any]) -> dict[str, Any]:
    family = str(item["family"])
    question = str(item["question"]).strip()
    gold_sparql = str(item["gold_sparql"]).strip()
    answer_type = str(item["answer_type"]).strip()
    source_id = str(item["id"]).strip()

    source_dataset = infer_source_dataset(family)
    schema_id = infer_schema_id(source_id, family)

    components = detect_query_components(gold_sparql)
    pattern_count = count_triple_patterns(gold_sparql)
    query_type = infer_query_type(components, answer_type)
    query_shape = infer_query_shape(gold_sparql)
    special_types = infer_special_types(components, answer_type, gold_sparql)
    complexity = infer_complexity_level(components, pattern_count)

    enriched = {
        "id": schema_id,
        "source_dataset": source_dataset,
        "source_id": source_id,
        "family": family,
        "split": "train",
        "language": "en",
        "question": question,
        "gold_sparql": gold_sparql,
        "query_type": query_type,
        "special_types": special_types,
        "answer_type": answer_type,
        "query_shape": query_shape,
        "number_of_patterns": pattern_count,
        "query_components": components,
        "complexity_level": complexity,
        "ambiguity_risk": "medium",
        "lexical_gap_risk": "medium",
        "hallucination_risk": "medium",
        "human_or_generated": "generated",
        "review_status": "reviewed",
        "gold_status": "draft",
    }

    if "_selection_review" in item:
        enriched["notes"] = (
            f"Selected from execution-reviewed green pool; "
            f"source candidate id={source_id}; "
            f"result_cardinality={item['_selection_review'].get('result_cardinality')}"
        )

    return enriched


def build_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_family: dict[str, int] = {}
    by_query_type: dict[str, int] = {}
    by_answer_type: dict[str, int] = {}
    by_complexity: dict[str, int] = {}

    for item in items:
        by_family[item["family"]] = by_family.get(item["family"], 0) + 1
        by_query_type[item["query_type"]] = by_query_type.get(item["query_type"], 0) + 1
        by_answer_type[item["answer_type"]] = by_answer_type.get(item["answer_type"], 0) + 1
        by_complexity[item["complexity_level"]] = by_complexity.get(item["complexity_level"], 0) + 1

    return {
        "total_items": len(items),
        "by_family": by_family,
        "by_query_type": by_query_type,
        "by_answer_type": by_answer_type,
        "by_complexity": by_complexity,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enrich selected green candidates toward the benchmark dataset schema."
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="Path to green_candidates_merged.json",
    )
    parser.add_argument(
        "--output-file",
        required=True,
        help="Path to save enriched candidates.",
    )
    parser.add_argument(
        "--summary-output-file",
        required=True,
        help="Path to save enrichment summary JSON.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting output files.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_path = Path(args.output_file)
    summary_path = Path(args.summary_output_file)

    raw_items = ensure_list_of_dicts(load_json_file(input_path), input_path)
    enriched_items = [enrich_item(item) for item in raw_items]
    summary = build_summary(enriched_items)

    save_json_file(output_path, enriched_items, overwrite=args.overwrite)
    save_json_file(summary_path, summary, overwrite=args.overwrite)

    print(f"Saved enriched candidates to: {output_path}")
    print(f"Saved enrichment summary to: {summary_path}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise