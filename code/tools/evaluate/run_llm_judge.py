"""Post-hoc LLM judge for semantic Text-to-SPARQL evaluation."""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

CODE_ROOT = Path(__file__).resolve().parents[2]
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from src.utils.config_loader import get_model_entry, load_json_config  # noqa: E402

AUTO_PREDICTION_FIELDS = [
    "pgmr_restored_query",
    "restored_query",
    "extracted_query",
    "predicted_query",
    "raw_model_output",
]

EXPLICIT_PREDICTION_FIELDS = [
    "auto",
    "extracted_query",
    "pgmr_restored_query",
    "restored_query",
    "raw_model_output",
]

GOLD_FIELDS = ["gold_sparql", "gold_query"]
SCORE_FIELDS = [
    "intent_score",
    "schema_score",
    "projection_score",
    "constraint_score",
    "aggregation_score",
]
VERDICTS = {"correct", "partially_correct", "incorrect"}


def _non_empty_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def load_benchmark_raw(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        results = payload.get("results")
        if not isinstance(results, list):
            raise ValueError("benchmark_raw.json object must contain a 'results' list.")
        return payload, results
    if isinstance(payload, list):
        return {}, payload
    raise ValueError("benchmark_raw.json must be either a list or an object.")


def select_gold_query(item: dict[str, Any]) -> tuple[str | None, str | None]:
    for field in GOLD_FIELDS:
        value = _non_empty_text(item.get(field))
        if value is not None:
            return value, field
    return None, None


def select_prediction_query(
    item: dict[str, Any],
    prediction_field_mode: str,
) -> tuple[str | None, str | None, bool]:
    if prediction_field_mode != "auto":
        value = _non_empty_text(item.get(prediction_field_mode))
        return value, prediction_field_mode if value is not None else None, (
            prediction_field_mode == "raw_model_output" and value is not None
        )

    for field in AUTO_PREDICTION_FIELDS:
        value = _non_empty_text(item.get(field))
        if value is not None:
            return value, field, field == "raw_model_output"
    return None, None, False


def get_family(item: dict[str, Any]) -> str:
    family = _non_empty_text(item.get("family"))
    if family:
        return family
    entry_metadata = item.get("entry_metadata")
    if isinstance(entry_metadata, dict):
        family = _non_empty_text(entry_metadata.get("family"))
        if family:
            return family
    return ""


def _metric_value(item: dict[str, Any], metric_name: str) -> Any:
    for container_name in ["validation", "metrics"]:
        container = item.get(container_name)
        if isinstance(container, dict) and metric_name in container:
            metric = container[metric_name]
            if isinstance(metric, dict):
                return metric.get("value")
            return metric
    if metric_name in item:
        return item.get(metric_name)
    return None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "ok", "success"}:
            return True
        if lowered in {"false", "0", "no", "error", "failed"}:
            return False
    return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def item_matches_filters(
    item: dict[str, Any],
    *,
    only_failures: bool,
    only_executable: bool,
) -> bool:
    if only_executable:
        execution = _as_bool(_metric_value(item, "prediction_execution_success"))
        if execution is False:
            return False

    if not only_failures:
        return True

    exact_match = _as_bool(_metric_value(item, "answer_exact_match"))
    answer_f1 = _as_float(_metric_value(item, "answer_f1"))

    if exact_match is False:
        return True
    if answer_f1 is not None and answer_f1 < 1.0:
        return True
    if exact_match is True or answer_f1 is not None:
        return False
    return True


def build_judge_prompt(
    *,
    question: str,
    family: str,
    gold_sparql: str,
    predicted_sparql: str,
) -> str:
    return f"""You are an evaluator for Text-to-SPARQL outputs for ORKG template questions.

You will receive:
- a natural language question
- the template family
- a gold SPARQL query
- a predicted SPARQL query

Your task is not exact string matching.
Judge whether the predicted SPARQL query is semantically appropriate for the question.

Important:
The gold query is a reference, but it may contain more SELECT variables than the question strictly requires.
Do not penalize the predicted query only because it selects fewer or different variables if the selected variables are semantically sufficient for the question.

Evaluate only the query text. Do not assume access to execution results.

Scoring rubric:

intent_score: 0-2
- 0 = wrong topic or wrong task
- 1 = partially captures the question intent
- 2 = captures the main question intent

schema_score: 0-2
- 0 = wrong ORKG template family or mostly wrong properties/classes
- 1 = partially correct ORKG structure
- 2 = central ORKG classes/properties are correct

projection_score: 0-2
- 0 = SELECT variables do not answer the question
- 1 = SELECT variables are partly useful but incomplete or overloaded
- 2 = SELECT variables are semantically appropriate for the question

constraint_score: 0-2
- 0 = important constraints are missing or wrong
- 1 = some constraints are correct, others missing
- 2 = relevant constraints are correct

aggregation_score: 0-2
- 0 = aggregation is wrong or missing when clearly required
- 1 = aggregation is partly appropriate or ambiguous
- 2 = aggregation is correct, or aggregation is correctly not needed

overall_score: 0-10
- Use the full 0-10 scale.
- This should usually match the sum of the five 0-2 rubric scores.

verdict must be exactly one of:
- correct
- partially_correct
- incorrect

Return only valid JSON:
{{
  "intent_score": 0,
  "schema_score": 0,
  "projection_score": 0,
  "constraint_score": 0,
  "aggregation_score": 0,
  "overall_score": 0,
  "verdict": "correct",
  "main_issue": "",
  "short_rationale": ""
}}

Question:
{question}

Family:
{family}

Gold SPARQL:
{gold_sparql}

Predicted SPARQL:
{predicted_sparql}
"""


def _extract_json_object(text: str) -> str:
    stripped = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    if fenced:
        stripped = fenced.group(1).strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start : end + 1]
    return stripped


def parse_judge_response(raw_text: str) -> dict[str, Any]:
    parsed = json.loads(_extract_json_object(raw_text))
    if not isinstance(parsed, dict):
        raise ValueError("Judge response JSON must be an object.")

    normalized: dict[str, Any] = {}
    for field in SCORE_FIELDS:
        score = int(parsed.get(field, 0))
        if score < 0 or score > 2:
            raise ValueError(f"{field} must be between 0 and 2.")
        normalized[field] = score

    overall = int(parsed.get("overall_score", sum(normalized.values())))
    if overall < 0 or overall > 10:
        raise ValueError("overall_score must be between 0 and 10.")
    normalized["overall_score"] = overall

    verdict = normalize_verdict(parsed.get("verdict"))
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {sorted(VERDICTS)}.")
    normalized["verdict"] = verdict
    normalized["main_issue"] = str(parsed.get("main_issue", "") or "")
    normalized["short_rationale"] = str(parsed.get("short_rationale", "") or "")
    return normalized


def normalize_verdict(value: Any) -> str:
    verdict = str(value or "").strip().lower()
    verdict = re.sub(r"[\s-]+", "_", verdict)
    if verdict in {"partial", "partly_correct", "partially"}:
        return "partially_correct"
    return verdict


def resolve_judge_model(
    model_selector: str,
    *,
    config_path: Path = CODE_ROOT / "config" / "model_config.json",
) -> tuple[str, str]:
    if config_path.exists():
        try:
            config = load_json_config(config_path)
            entry = get_model_entry(config, model_selector)
        except Exception:
            return model_selector, "OPENAI_API_KEY"
        api = entry.get("api", {}) if isinstance(entry.get("api"), dict) else {}
        return (
            str(entry.get("model_id") or model_selector),
            str(api.get("api_key_env") or api.get("env_var_name") or "OPENAI_API_KEY"),
        )
    return model_selector, "OPENAI_API_KEY"


def call_llm_judge(client: Any, *, model_id: str, prompt: str) -> dict[str, Any]:
    request_kwargs: dict[str, Any] = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }
    if not model_id.startswith("gpt-5"):
        request_kwargs["temperature"] = 0.0

    completion = client.chat.completions.create(**request_kwargs)
    raw_text = completion.choices[0].message.content
    if not raw_text or not raw_text.strip():
        raise ValueError("Judge returned an empty response.")
    return parse_judge_response(raw_text)


def create_judge_client(env_var_name: str) -> Any:
    from src.core.openai_provider import create_openai_client

    return create_openai_client(env_var_name=env_var_name)


def build_skipped_record(
    *,
    item: dict[str, Any],
    prediction_field_used: str | None,
    gold_field_used: str | None,
    skip_reason: str,
) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or item.get("uid") or ""),
        "question": str(item.get("question") or ""),
        "family": get_family(item),
        "prediction_field_used": prediction_field_used,
        "gold_field_used": gold_field_used,
        "used_raw_model_output_fallback": prediction_field_used == "raw_model_output",
        "intent_score": 0,
        "schema_score": 0,
        "projection_score": 0,
        "constraint_score": 0,
        "aggregation_score": 0,
        "overall_score": 0,
        "verdict": "incorrect",
        "main_issue": "",
        "short_rationale": "",
        "skipped": True,
        "skip_reason": skip_reason,
    }


def build_judged_record(
    *,
    item: dict[str, Any],
    prediction_field_used: str,
    gold_field_used: str,
    used_raw_model_output_fallback: bool,
    judgment: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or item.get("uid") or ""),
        "question": str(item.get("question") or ""),
        "family": get_family(item),
        "prediction_field_used": prediction_field_used,
        "gold_field_used": gold_field_used,
        "used_raw_model_output_fallback": used_raw_model_output_fallback,
        **judgment,
        "skipped": False,
        "skip_reason": None,
    }


def prepare_items(
    items: list[dict[str, Any]],
    *,
    only_failures: bool,
    only_executable: bool,
    max_items: int | None,
    sample_seed: int,
) -> list[dict[str, Any]]:
    filtered = [
        item
        for item in items
        if item_matches_filters(
            item,
            only_failures=only_failures,
            only_executable=only_executable,
        )
    ]
    if max_items is not None and max_items < len(filtered):
        rng = random.Random(sample_seed)
        indexed = list(enumerate(filtered))
        sampled = rng.sample(indexed, max_items)
        return [item for _, item in sorted(sampled, key=lambda pair: pair[0])]
    return filtered


def build_summary(
    records: list[dict[str, Any]],
    *,
    num_input_items: int,
    judge_model: str,
    prediction_field_mode: str,
) -> dict[str, Any]:
    judged = [record for record in records if not record.get("skipped")]
    skipped = [record for record in records if record.get("skipped")]
    zero_scored = [
        record
        for record in records
        if _as_float(record.get("overall_score")) == 0.0
    ]

    def mean(field: str) -> float | None:
        values = [_as_float(record.get(field)) for record in records]
        valid = [value for value in values if value is not None]
        if not valid:
            return None
        return sum(valid) / len(valid)

    return {
        "num_input_items": num_input_items,
        "num_judged_items": len(judged),
        "num_skipped_items": len(skipped),
        "num_zero_scored_items": len(zero_scored),
        "judge_model": judge_model,
        "prediction_field_mode": prediction_field_mode,
        "mean_intent_score": mean("intent_score"),
        "mean_schema_score": mean("schema_score"),
        "mean_projection_score": mean("projection_score"),
        "mean_constraint_score": mean("constraint_score"),
        "mean_aggregation_score": mean("aggregation_score"),
        "mean_overall_score": mean("overall_score"),
        "verdict_counts": dict(Counter(record.get("verdict") for record in records)),
        "prediction_field_used_counts": dict(
            Counter(
                record.get("prediction_field_used")
                for record in records
                if record.get("prediction_field_used")
            )
        ),
        "skip_reason_counts": dict(
            Counter(
                record.get("skip_reason")
                for record in skipped
                if record.get("skip_reason")
            )
        ),
        "zero_score_reason_counts": dict(
            Counter(
                record.get("skip_reason") or "judged_zero_score"
                for record in zero_scored
            )
        ),
    }


def run_llm_judge(
    *,
    input_path: Path,
    output_dir: Path,
    judge_model: str,
    prediction_field_mode: str,
    max_items: int | None,
    only_failures: bool,
    only_executable: bool,
    sample_seed: int,
    dry_run: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _, input_items = load_benchmark_raw(input_path)
    selected_items = prepare_items(
        input_items,
        only_failures=only_failures,
        only_executable=only_executable,
        max_items=max_items,
        sample_seed=sample_seed,
    )
    model_id, env_var_name = resolve_judge_model(judge_model)
    client = None if dry_run else create_judge_client(env_var_name=env_var_name)

    records: list[dict[str, Any]] = []
    for item in selected_items:
        gold_query, gold_field_used = select_gold_query(item)
        prediction_query, prediction_field_used, used_raw_fallback = (
            select_prediction_query(item, prediction_field_mode)
        )

        if gold_query is None:
            records.append(
                build_skipped_record(
                    item=item,
                    prediction_field_used=prediction_field_used,
                    gold_field_used=gold_field_used,
                    skip_reason="missing_gold",
                )
            )
            continue
        if prediction_query is None:
            records.append(
                build_skipped_record(
                    item=item,
                    prediction_field_used=prediction_field_used,
                    gold_field_used=gold_field_used,
                    skip_reason="missing_prediction",
                )
            )
            continue
        if dry_run:
            records.append(
                build_skipped_record(
                    item=item,
                    prediction_field_used=prediction_field_used,
                    gold_field_used=gold_field_used,
                    skip_reason="dry_run",
                )
            )
            continue

        prompt = build_judge_prompt(
            question=str(item.get("question") or ""),
            family=get_family(item),
            gold_sparql=gold_query,
            predicted_sparql=prediction_query,
        )
        try:
            assert client is not None
            judgment = call_llm_judge(client, model_id=model_id, prompt=prompt)
        except Exception as exc:
            records.append(
                build_skipped_record(
                    item=item,
                    prediction_field_used=prediction_field_used,
                    gold_field_used=gold_field_used,
                    skip_reason=f"judge_error:{exc}",
                )
            )
            continue

        records.append(
            build_judged_record(
                item=item,
                prediction_field_used=prediction_field_used or "",
                gold_field_used=gold_field_used or "",
                used_raw_model_output_fallback=used_raw_fallback,
                judgment=judgment,
            )
        )

    summary = build_summary(
        records,
        num_input_items=len(input_items),
        judge_model=model_id,
        prediction_field_mode=prediction_field_mode,
    )
    write_outputs(output_dir=output_dir, records=records, summary=summary)
    return records, summary


def write_outputs(
    *,
    output_dir: Path,
    records: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "llm_judge_raw.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "llm_judge_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    benchmark_summary_path = output_dir / "benchmark_summary.json"
    if benchmark_summary_path.exists():
        benchmark_summary = json.loads(
            benchmark_summary_path.read_text(encoding="utf-8")
        )
        benchmark_summary["llm_judge"] = summary
        (output_dir / "benchmark_summary_with_llm_judge.json").write_text(
            json.dumps(benchmark_summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a post-hoc LLM judge over benchmark_raw.json."
    )
    parser.add_argument("--input", required=True, help="Path to benchmark_raw.json.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where llm_judge_raw.json and llm_judge_summary.json are written.",
    )
    parser.add_argument(
        "--judge-model",
        default="gpt_4o_mini",
        help="OpenAI model config key or model id for judging.",
    )
    parser.add_argument(
        "--prediction-field",
        default="auto",
        choices=EXPLICIT_PREDICTION_FIELDS,
        help="Prediction query field to judge. Auto prefers restored queries.",
    )
    parser.add_argument("--max-items", type=int, default=None)
    parser.add_argument("--only-failures", action="store_true")
    parser.add_argument("--only-executable", action="store_true")
    parser.add_argument("--sample-seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records, summary = run_llm_judge(
        input_path=Path(args.input),
        output_dir=Path(args.output_dir),
        judge_model=args.judge_model,
        prediction_field_mode=args.prediction_field,
        max_items=args.max_items,
        only_failures=args.only_failures,
        only_executable=args.only_executable,
        sample_seed=args.sample_seed,
        dry_run=args.dry_run,
    )
    print(f"Input items:   {summary['num_input_items']}")
    print(f"Output records:{len(records)}")
    print(f"Judged items:  {summary['num_judged_items']}")
    print(f"Skipped items: {summary['num_skipped_items']}")
    print(f"Saved raw:     {Path(args.output_dir) / 'llm_judge_raw.json'}")
    print(f"Saved summary: {Path(args.output_dir) / 'llm_judge_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
