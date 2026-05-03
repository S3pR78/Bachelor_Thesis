from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


PARAPHRASE_FIELDS = [
    "paraphrased_questions",
    "paraphrases",
    "question_paraphrases",
]


def load_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return data


def save_json(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_question(text: str) -> str:
    return " ".join(text.strip().lower().split())


def extract_paraphrases(item: dict[str, Any]) -> list[str]:
    paraphrases: list[str] = []

    for field in PARAPHRASE_FIELDS:
        value = item.get(field)
        if not value:
            continue

        if isinstance(value, list):
            for entry in value:
                if isinstance(entry, str):
                    paraphrases.append(entry)
                elif isinstance(entry, dict):
                    q = entry.get("question") or entry.get("text") or entry.get("paraphrase")
                    if isinstance(q, str):
                        paraphrases.append(q)

    cleaned: list[str] = []
    seen: set[str] = set()

    original_question = normalize_question(str(item.get("question", "")))

    for paraphrase in paraphrases:
        paraphrase = paraphrase.strip()
        if not paraphrase:
            continue

        key = normalize_question(paraphrase)

        if key == original_question:
            continue

        if key in seen:
            continue

        cleaned.append(paraphrase)
        seen.add(key)

    return cleaned


def make_paraphrase_item(
    item: dict[str, Any],
    paraphrase: str,
    index: int,
    drop_paraphrase_fields: bool,
) -> dict[str, Any]:
    new_item = dict(item)

    original_id = str(item["id"])

    new_item["id"] = f"{original_id}__para_{index:02d}"
    new_item["source_id"] = str(item.get("source_id", original_id))
    new_item["original_id"] = original_id
    new_item["question"] = paraphrase
    new_item["is_paraphrase"] = True
    new_item["paraphrase_index"] = index

    # Important: keep gold_sparql / gold_pgmr_sparql unchanged.
    # The paraphrase has the same intended query as the original question.

    if drop_paraphrase_fields:
        for field in PARAPHRASE_FIELDS:
            new_item.pop(field, None)

    return new_item


def make_original_item(
    item: dict[str, Any],
    drop_paraphrase_fields: bool,
) -> dict[str, Any]:
    new_item = dict(item)
    new_item["is_paraphrase"] = False

    if drop_paraphrase_fields:
        for field in PARAPHRASE_FIELDS:
            new_item.pop(field, None)

    return new_item


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expand a training dataset by turning existing paraphrased questions into additional training examples."
    )

    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)

    parser.add_argument(
        "--max-paraphrases-per-item",
        type=int,
        default=None,
        help="Optional cap per original item.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )
    parser.add_argument(
        "--shuffle",
        action="store_true",
        help="Shuffle final output deterministically.",
    )
    parser.add_argument(
        "--drop-paraphrase-fields",
        action="store_true",
        help="Remove paraphrased_questions/paraphrases fields from output items.",
    )
    parser.add_argument(
        "--allow-non-train",
        action="store_true",
        help="Allow input items whose split is not train.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    data = load_json(args.input)

    expanded: list[dict[str, Any]] = []
    total_paraphrases = 0
    items_without_paraphrases = 0

    rng = random.Random(args.seed)

    for item in data:
        if "id" not in item:
            raise ValueError(f"Item without id: {item}")

        if not args.allow_non_train and item.get("split") != "train":
            raise ValueError(
                f"Input contains non-train item id={item.get('id')} split={item.get('split')}. "
                "Use --allow-non-train only if this is intentional."
            )

        expanded.append(
            make_original_item(
                item,
                drop_paraphrase_fields=args.drop_paraphrase_fields,
            )
        )

        paraphrases = extract_paraphrases(item)

        if args.max_paraphrases_per_item is not None:
            paraphrases = paraphrases[: args.max_paraphrases_per_item]

        if not paraphrases:
            items_without_paraphrases += 1

        for idx, paraphrase in enumerate(paraphrases, start=1):
            expanded.append(
                make_paraphrase_item(
                    item,
                    paraphrase=paraphrase,
                    index=idx,
                    drop_paraphrase_fields=args.drop_paraphrase_fields,
                )
            )
            total_paraphrases += 1

    ids = [str(item["id"]) for item in expanded]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate ids after paraphrase expansion.")

    if args.shuffle:
        rng.shuffle(expanded)

    save_json(args.output, expanded)

    print("Input items:", len(data))
    print("Output items:", len(expanded))
    print("Added paraphrase items:", total_paraphrases)
    print("Items without paraphrases:", items_without_paraphrases)
    print("Output:", args.output)


if __name__ == "__main__":
    main()