from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from src.sparql.execution import execute_sparql_query
from src.sparql.prefixes import prepend_orkg_prefixes
from tools.pgmr.evaluate_model_outputs import postprocess_pgmr_query


PGMR_TOKEN_PATTERN = re.compile(r"\b(?:pgmr|pgmrc):[A-Za-z_][A-Za-z0-9_]*\b")
ORKG_TOKEN_PATTERN = re.compile(r"\b(?:orkgp|orkgc|orkgr):[A-Za-z0-9_]+\b")


MANUAL_FALLBACK_MAP = {
    # Core ORKG paper/contribution pattern.
    "pgmr:has_contribution": "orkgp:P31",
    "pgmr:publication_year": "orkgp:P29",

    # Safe alias observed in model output:
    # gold PGMR uses pgmr:statistical_tests -> orkgp:P35133.
    "pgmr:statistical_test": "orkgp:P35133",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_id(value: Any) -> str:
    return str(value).strip()


def find_strings(obj: Any) -> list[str]:
    values: list[str] = []

    if isinstance(obj, str):
        values.append(obj)
    elif isinstance(obj, dict):
        for value in obj.values():
            values.extend(find_strings(value))
    elif isinstance(obj, list):
        for value in obj:
            values.extend(find_strings(value))

    return values


def extract_mapping_pairs_from_object(obj: Any) -> dict[str, str]:
    """
    Flexible extractor for different possible mapping structures.

    It looks for any dict/list containing one PGMR token and one ORKG token.
    This works for many shapes such as:
      {"pgmr": "pgmr:evaluation", "original": "orkgp:P123"}
      {"placeholder": "pgmrc:nlp4re_contribution", "target": "orkgc:C121001"}
      [{"from": "orkgp:P31", "to": "pgmr:has_contribution"}, ...]
    """
    mapping: dict[str, str] = {}

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            strings = find_strings(value)
            pgmr_tokens = []
            orkg_tokens = []

            for text in strings:
                pgmr_tokens.extend(PGMR_TOKEN_PATTERN.findall(text))
                orkg_tokens.extend(ORKG_TOKEN_PATTERN.findall(text))

            pgmr_tokens = sorted(set(pgmr_tokens))
            orkg_tokens = sorted(set(orkg_tokens))

            if len(pgmr_tokens) == 1 and len(orkg_tokens) == 1:
                mapping[pgmr_tokens[0]] = orkg_tokens[0]

            for child in value.values():
                walk(child)

        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(obj)
    return mapping


def load_memory_mapping(memory_dir: Path | None) -> dict[str, str]:
    if memory_dir is None:
        return {}

    if not memory_dir.exists():
        return {}

    mapping: dict[str, str] = {}

    for path in sorted(memory_dir.rglob("*.json")):
        try:
            data = load_json(path)
        except Exception:
            continue

        mapping.update(extract_mapping_pairs_from_object(data))

    return mapping


def build_entry_mapping(entry: dict[str, Any], memory_mapping: dict[str, str]) -> dict[str, str]:
    mapping = dict(MANUAL_FALLBACK_MAP)
    mapping.update(memory_mapping)

    # Entry-specific mappings should win if present.
    for field in ["pgmr_replaced_terms", "pgmr_mappings", "pgmr_mapping", "replaced_terms"]:
        if field in entry:
            mapping.update(extract_mapping_pairs_from_object(entry[field]))

    return mapping


def restore_pgmr_query(pgmr_query: str, mapping: dict[str, str]) -> tuple[str, list[str]]:
    missing: list[str] = []

    def replace_token(match: re.Match[str]) -> str:
        token = match.group(0)
        replacement = mapping.get(token)

        if replacement is None:
            missing.append(token)
            return token

        return replacement

    restored = PGMR_TOKEN_PATTERN.sub(replace_token, pgmr_query)
    return restored, sorted(set(missing))


def detect_basic_query_status(query: str) -> dict[str, Any]:
    return {
        "starts_with_query_type": bool(re.match(r"^\s*(SELECT|ASK|CONSTRUCT|DESCRIBE)\b", query, re.I)),
        "has_where_block": bool(re.search(r"\bWHERE\s*\{", query, re.I)),
        "balanced_braces": query.count("{") == query.count("}"),
        "remaining_pgmr_tokens": sorted(set(PGMR_TOKEN_PATTERN.findall(query))),
        "orkg_tokens": sorted(set(ORKG_TOKEN_PATTERN.findall(query))),
    }


def execute_query_if_requested(
    query: str,
    endpoint: str | None,
    timeout_seconds: int,
) -> dict[str, Any]:
    if endpoint is None:
        return {
            "execution_status": "not_requested",
            "execution_error": None,
            "result_summary": None,
        }

    try:
        full_query = prepend_orkg_prefixes(query)
        response = execute_sparql_query(
            query=full_query,
            endpoint_url=endpoint,
            timeout_seconds=timeout_seconds,
        )

        bindings = (
            response.get("results", {}).get("bindings", [])
            if isinstance(response, dict)
            else []
        )

        boolean = response.get("boolean") if isinstance(response, dict) else None

        return {
            "execution_status": "ok",
            "execution_error": None,
            "result_summary": {
                "binding_count": len(bindings),
                "boolean": boolean,
                "top_level_keys": sorted(response.keys()) if isinstance(response, dict) else [],
            },
        }

    except Exception as exc:
        return {
            "execution_status": "error",
            "execution_error": str(exc),
            "result_summary": None,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Restore PGMR-lite model predictions to executable ORKG SPARQL and optionally execute them."
    )
    parser.add_argument("--report", type=Path, required=True, help="PGMR model evaluation report JSON.")
    parser.add_argument("--dataset", type=Path, required=True, help="Original PGMR dataset split JSON.")
    parser.add_argument("--output", type=Path, required=True, help="Output restoration/execution report JSON.")
    parser.add_argument("--memory-dir", type=Path, default=Path("code/data/orkg_memory/templates"))
    parser.add_argument("--endpoint", default=None, help="Optional SPARQL endpoint URL.")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--prediction-field", default="postprocessed_prediction")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    report = load_json(args.report)
    dataset = load_json(args.dataset)

    if not isinstance(dataset, list):
        raise ValueError("Dataset must be a JSON list.")

    dataset_by_id = {normalize_id(entry.get("id")): entry for entry in dataset if isinstance(entry, dict)}

    results = report.get("results", [])
    if not isinstance(results, list):
        raise ValueError("Report must contain a list field named 'results'.")

    selected_results = results[: args.limit] if args.limit is not None else results

    memory_mapping = load_memory_mapping(args.memory_dir)

    output_results: list[dict[str, Any]] = []
    counters = Counter()

    for index, result in enumerate(selected_results):
        result_id = normalize_id(result.get("id"))
        entry = dataset_by_id.get(result_id)

        if entry is None:
            counters["missing_dataset_entry"] += 1
            output_results.append(
                {
                    "index": index,
                    "id": result_id,
                    "restore_status": "missing_dataset_entry",
                }
            )
            continue

        pgmr_prediction = str(result.get(args.prediction_field, "")).strip()

        entry_mapping = build_entry_mapping(entry, memory_mapping)
        restored_query, missing_tokens = restore_pgmr_query(pgmr_prediction, entry_mapping)
        restored_query = postprocess_pgmr_query(restored_query)
        basic_status = detect_basic_query_status(restored_query)

        if missing_tokens:
            restore_status = "missing_mapping"
        elif basic_status["remaining_pgmr_tokens"]:
            restore_status = "remaining_pgmr_tokens"
        else:
            restore_status = "ok"

        execution = execute_query_if_requested(
            query=restored_query,
            endpoint=args.endpoint,
            timeout_seconds=args.timeout_seconds,
        )

        counters[f"restore_status:{restore_status}"] += 1
        counters[f"execution_status:{execution['execution_status']}"] += 1

        if missing_tokens:
            counters["items_with_missing_tokens"] += 1

        if basic_status["remaining_pgmr_tokens"]:
            counters["items_with_remaining_pgmr_tokens"] += 1

        output_results.append(
            {
                "index": index,
                "id": result_id,
                "family": entry.get("family"),
                "question": entry.get("question"),
                "gold_pgmr_sparql": entry.get("gold_pgmr_sparql"),
                "pgmr_prediction": pgmr_prediction,
                "restored_prediction": restored_query,
                "restore_status": restore_status,
                "missing_mapping_tokens": missing_tokens,
                "basic_status": basic_status,
                "execution": execution,
            }
        )

        print(
            f"[{index + 1}/{len(selected_results)}] "
            f"id={result_id} restore={restore_status} exec={execution['execution_status']}"
        )

    summary = {
        "report": str(args.report),
        "dataset": str(args.dataset),
        "memory_dir": str(args.memory_dir),
        "endpoint": args.endpoint,
        "total_items": len(selected_results),
        "memory_mapping_size": len(memory_mapping),
        "counts": dict(counters),
    }

    save_json(
        args.output,
        {
            "summary": summary,
            "results": output_results,
        },
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
