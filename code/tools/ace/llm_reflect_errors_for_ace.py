import argparse
import json
import os
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from openai import OpenAI


BAD_GENERIC_PHRASES = [
    "return only",
    "no markdown",
    "no explanation",
    "use valid",
    "generate better",
    "complete query",
    "valid pgmr",
    "do not explain",
    "only the query",
    "supported forms",
    "unsupported query forms",
    "answer format",
    "expected structure",
    "executable complete",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_traces(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ["traces", "error_traces", "items", "results"]:
            value = data.get(key)
            if isinstance(value, list):
                return value

    raise ValueError("Could not find traces list in input JSON.")


def select_traces(
    traces: list[dict[str, Any]],
    family: str,
    max_traces: int,
) -> list[dict[str, Any]]:
    family_items = [t for t in traces if t.get("family") == family]

    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    priority_categories = [
        "invalid_filter_triple_pattern",
        "relation_like_object",
        "markdown_fence_leak",
        "invalid_property_path_mixture",
        "pgmr_restore_error",
        "pgmr_unmapped_placeholders",
        "predicate_ref_mismatch",
        "answer_mismatch",
        "query_form_mismatch",
        "prediction_execution_error",
        "endpoint_bad_request",
        "no_extracted_query",
    ]

    for category in priority_categories:
        for t in family_items:
            item_id = str(t.get("item_id"))
            cats = t.get("categories") or []
            if item_id in seen_ids:
                continue
            if category in cats:
                selected.append(t)
                seen_ids.add(item_id)
                break

    for t in family_items:
        if len(selected) >= max_traces:
            break

        item_id = str(t.get("item_id"))
        if item_id in seen_ids:
            continue

        selected.append(t)
        seen_ids.add(item_id)

    return selected[:max_traces]


def truncate_text(value: Any, max_chars: int = 2600) -> Any:
    if not isinstance(value, str):
        return value
    if len(value) <= max_chars:
        return value
    return value[:max_chars] + "\n...[truncated]"


def compact_trace(t: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": str(t.get("item_id")),
        "family": t.get("family"),
        "question": t.get("question"),
        "categories": t.get("categories"),
        "metrics": t.get("metrics"),
        "raw_model_output": truncate_text(t.get("raw_model_output")),
        "extracted_query": truncate_text(t.get("extracted_query")),
        "restored_query": truncate_text(t.get("restored_query")),
        "gold_sparql": truncate_text(t.get("gold_sparql")),
        "error_text": truncate_text(t.get("error_text")),
        "source": t.get("source"),
    }


def current_rules(playbook: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not playbook:
        return []

    out = []
    for b in playbook.get("bullets", []):
        if not b.get("enabled", True):
            continue

        out.append(
            {
                "title": b.get("title"),
                "category": b.get("category"),
                "content": b.get("content"),
                "avoid": b.get("avoid"),
                "priority": b.get("priority"),
                "source": b.get("source"),
            }
        )

    return out


def family_hints(family: str) -> str:
    if family == "nlp4re":
        return """
Family hints for nlp4re:
- Core PGMR pattern: ?paper pgmr:has_contribution ?contribution . ?contribution a pgmrc:nlp4re_contribution .
- A PGMR triple must be subject relation object.
- Do not use relation-like pgmr:/pgmrc: tokens as objects of another pgmr: relation.
- For named concepts such as classification, bind a variable and filter its rdfs:label instead of inventing pgmrc classes.
- Do not put triple patterns inside FILTER. FILTER is only for expressions over already bound variables.
- NLP task type questions usually need contribution -> NLP task -> task type/label.
- Evaluation questions usually need contribution -> evaluation -> metric/baseline/validation.
- Dataset questions usually need contribution -> NLP dataset -> nested dataset field.
""".strip()

    if family == "empirical_research_practice":
        return """
Family hints for empirical_research_practice:
- Core PGMR pattern: ?paper pgmr:has_contribution ?contribution . ?contribution a pgmrc:empirical_research_practice_contribution .
- A PGMR triple must be subject relation object.
- Do not use relation-like pgmr:/pgmrc: tokens as objects of another pgmr: relation.
- For named concepts such as accuracy, recall, construct validity, or internal validity, bind a variable and filter its rdfs:label instead of inventing pgmr:/pgmrc: objects.
- Do not put triple patterns inside FILTER. FILTER is only for expressions over already bound variables.
- Venue questions use the contribution venue path.
- Data collection questions use contribution -> data collection -> method/data.
- Data analysis questions use contribution -> data analysis -> machine learning/statistics -> requested field.
- Validity threat questions should bind the validity/threat node and filter labels when a specific threat type is requested.
""".strip()

    return ""


def build_prompt(
    family: str,
    mode: str,
    local_model: str,
    traces: list[dict[str, Any]],
    playbook: dict[str, Any] | None,
    max_rules: int,
) -> str:
    compact = [compact_trace(t) for t in traces]
    rules = current_rules(playbook)

    return f"""
Du bist ein LLM-assisted Reflector für eine Bachelorarbeit zu Text-to-SPARQL auf ORKG-Templates.

Aufgabe:
Analysiere Fehler-Traces eines lokalen Base-Modells und erzeuge kurze, konkrete ACE-Playbook-Regeln.

Kontext:
- Lokales Modell: {local_model}
- Familie: {family}
- Modus: {mode}
- Repräsentation: PGMR-lite mit pgmr:/pgmrc:-Platzhaltern
- Die Regeln werden später in den Prompt eingefügt.
- Diese Traces stammen aus einem ACE-Development-Sample, NICHT aus dem finalen Benchmark.

Arbeitsweise:
Für jeden Trace sollst du vergleichen:
1. die natürliche Frage,
2. die gold_sparql Struktur,
3. raw_model_output,
4. extracted_query/restored_query,
5. categories, metrics und error_text.

Finde zuerst den konkreten strukturellen Fehler im Modelloutput.
Generalisiere danach nur wiederkehrende oder klare Fehler zu kurzen ACE-Regeln.

Sehr wichtig:
- Erzeuge KEINE generischen Regeln wie "Return only the query", "Use valid placeholders", "No markdown", "Generate executable queries".
- Erzeuge konkrete Struktur-, Pfad-, Mapping-, Label-Filter-, FILTER-, Triple-Structure- oder Placeholder-Choice-Regeln.
- Schreibe KEINE korrigierten Queries.
- Kopiere KEINE echten ORKG-IDs in PGMR-lite-Regeln.
- Wenn gold_sparql echte ORKG-IDs enthält, übersetze die Beobachtung in eine PGMR-lite-Strukturregel.
- Verwende keine Regeln, die nur sagen, dass die Query "besser" oder "gültig" sein soll.
- Regeln sollen kurz sein, weil sie in den Prompt kommen.
- Dedupliziere ähnliche Regeln.
- Ausgabe NUR als valides JSON-Array, keine Markdown-Erklärung.

{family_hints(family)}

Gute Regel-Beispiele:
[
  {{
    "category": "filter_pattern",
    "title": "Keep triple patterns outside FILTER",
    "content": "Use FILTER only for expressions over bound variables. Write subject-relation-object triples outside FILTER, then filter labels or values.",
    "avoid": "Do not write FILTER(?x pgmr:relation pgmr:value).",
    "priority": 124,
    "evidence_item_ids": ["example_id"]
  }},
  {{
    "category": "triple_structure",
    "title": "Do not use relation-like tokens as objects",
    "content": "A PGMR triple must be subject relation object. For named concepts, bind a variable and filter its rdfs:label.",
    "avoid": "Do not write ?x pgmr:relation pgmr:concept.",
    "priority": 123,
    "evidence_item_ids": ["example_id"]
  }},
  {{
    "category": "label_filter",
    "title": "Use label filters for named concepts",
    "content": "For named concepts such as classification or construct validity, bind the relevant node and filter its rdfs:label.",
    "avoid": "Do not invent pgmr:/pgmrc: objects for named concepts.",
    "priority": 118,
    "evidence_item_ids": ["example_id"]
  }}
]

Schlechte Regeln:
[
  {{
    "category": "output_format",
    "title": "Return only the query",
    "content": "Return only the final query.",
    "avoid": "Do not explain.",
    "priority": 120,
    "evidence_item_ids": []
  }},
  {{
    "category": "query_form_mismatch",
    "title": "Avoid unsupported query forms",
    "content": "Ensure the query form matches the expected structure.",
    "avoid": "Do not use unsupported forms.",
    "priority": 120,
    "evidence_item_ids": []
  }}
]

Regel-Schema:
[
  {{
    "category": "nested_path | predicate_ref_mismatch | answer_mismatch | query_form_mismatch | placeholder_choice | label_filter | contribution_pattern | filter_pattern | triple_structure",
    "title": "short imperative title",
    "content": "one concise rule, max 35 words",
    "avoid": "one concise anti-pattern, max 25 words",
    "priority": 90-125,
    "evidence_item_ids": ["id1", "id2"]
  }}
]

Maximal {max_rules} Regeln.

Aktuelles Playbook:
{json.dumps(rules, ensure_ascii=False, indent=2)}

Fehler-Traces:
{json.dumps(compact, ensure_ascii=False, indent=2)}
""".strip()


def extract_json_array(text: str) -> list[dict[str, Any]]:
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("[")
    end = text.rfind("]")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Could not find JSON array in model response:\n{text}")

    return json.loads(text[start:end + 1])


def is_generic(rule: dict[str, Any]) -> bool:
    text = " ".join(
        str(rule.get(k, "")).lower()
        for k in ["title", "content", "avoid", "category"]
    )
    return any(p in text for p in BAD_GENERIC_PHRASES)


def contains_direct_orkg(rule: dict[str, Any]) -> bool:
    text = " ".join(
        str(rule.get(k, "")).lower()
        for k in ["title", "content", "avoid"]
    )
    return any(marker in text for marker in ["orkgp:", "orkgc:", "orkgr:", "http://orkg.org/"])


def normalize_rule(
    rule: dict[str, Any],
    family: str,
    mode: str,
    source_model: str,
) -> dict[str, Any]:
    priority = int(rule.get("priority", 100))
    priority = max(80, min(125, priority))

    return {
        "family": family,
        "mode": mode,
        "category": str(rule.get("category", "answer_mismatch")).strip(),
        "title": str(rule.get("title", "")).strip(),
        "content": str(rule.get("content", "")).strip(),
        "avoid": str(rule.get("avoid", "")).strip(),
        "priority": priority,
        "evidence_item_ids": [str(x) for x in rule.get("evidence_item_ids", [])],
        "source": {
            "type": "llm_assisted_reflector",
            "model": source_model,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--error-traces", type=Path, required=True)
    parser.add_argument("--current-playbook", type=Path, required=False)
    parser.add_argument("--family", required=True)
    parser.add_argument("--mode", default="pgmr_lite")
    parser.add_argument("--local-model", required=True)
    parser.add_argument("--llm-model", default="gpt-4o-mini")
    parser.add_argument("--max-traces", type=int, default=20)
    parser.add_argument("--max-rules", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--save-prompt", type=Path)
    args = parser.parse_args()

    trace_data = load_json(args.error_traces)
    all_traces = get_traces(trace_data)
    traces = select_traces(all_traces, args.family, args.max_traces)

    if not traces:
        raise ValueError(f"No traces found for family={args.family}")

    playbook = load_json(args.current_playbook) if args.current_playbook else None

    prompt = build_prompt(
        family=args.family,
        mode=args.mode,
        local_model=args.local_model,
        traces=traces,
        playbook=playbook,
        max_rules=args.max_rules,
    )

    if args.save_prompt:
        args.save_prompt.parent.mkdir(parents=True, exist_ok=True)
        args.save_prompt.write_text(prompt, encoding="utf-8")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=args.llm_model,
        messages=[
            {
                "role": "system",
                "content": "You produce concise JSON ACE playbook rules for Text-to-SPARQL error correction. Return only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    text = response.choices[0].message.content or ""
    raw_rules = extract_json_array(text)

    cleaned: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for rule in raw_rules:
        nr = normalize_rule(rule, args.family, args.mode, args.llm_model)
        key = (nr["title"].lower(), nr["content"].lower())

        if not nr["title"] or not nr["content"]:
            continue

        if is_generic(nr):
            continue

        if args.mode == "pgmr_lite" and contains_direct_orkg(nr):
            continue

        if key in seen:
            continue

        seen.add(key)
        cleaned.append(nr)

    write_json(args.output, cleaned)

    print("family:", args.family)
    print("selected traces:", len(traces))
    print("rules written:", len(cleaned))
    print("output:", args.output)


if __name__ == "__main__":
    main()