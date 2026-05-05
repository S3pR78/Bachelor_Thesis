"""Import LLM-generated ACE rule candidates into an existing playbook."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GENERIC_PHRASES = [
    "return only",
    "no markdown",
    "no explanation",
    "generate valid",
    "generate better",
    "complete query",
    "unsupported query forms",
    "supported forms",
    "answer format matches",
    "unexpected format",
]

DIRECT_ORKG_MARKERS = [
    "orkgp:",
    "orkgc:",
    "orkgr:",
    "http://orkg.org/",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def norm(text: str) -> str:
    return " ".join((text or "").lower().split())


def stable_id(family: str, mode: str, title: str, content: str) -> str:
    h = hashlib.sha1(f"{family}|{mode}|{title}|{content}".encode("utf-8")).hexdigest()[:10]
    safe_family = family.replace("-", "_")
    safe_mode = mode.replace("-", "_")
    return f"{safe_family}_{safe_mode}_llm_{h}"


def is_generic(rule: dict[str, Any]) -> bool:
    text = norm(" ".join(str(rule.get(k, "")) for k in ["title", "content", "avoid", "category"]))
    return any(p in text for p in GENERIC_PHRASES)


def contains_direct_orkg(rule: dict[str, Any]) -> bool:
    text = " ".join(str(rule.get(k, "")) for k in ["title", "content", "avoid", "positive_pattern"]).lower()
    return any(marker in text for marker in DIRECT_ORKG_MARKERS)


def as_bullet(rule: dict[str, Any], family: str, mode: str, now: str) -> dict[str, Any]:
    title = str(rule.get("title", "")).strip()
    content = str(rule.get("content", "")).strip()
    avoid = str(rule.get("avoid", "")).strip()
    category = str(rule.get("category", "answer_mismatch")).strip()
    priority = int(rule.get("priority", 100))

    return {
        "id": stable_id(family, mode, title, content),
        "family": family,
        "mode": mode,
        "category": category,
        "title": title,
        "content": content,
        "bullet_type": "rule",
        "priority": max(80, min(125, priority)),
        "enabled": True,
        "avoid": avoid,
        "positive_pattern": "",
        "applicability": f"{family} {mode} queries.",
        "source": {
            "type": "llm_assisted_reflector",
            "model": rule.get("source_model"),
        },
        "source_model": rule.get("source_model"),
        "evidence_item_ids": [str(x) for x in rule.get("evidence_item_ids", [])],
        "helpful_count": 0,
        "harmful_count": 0,
        "created_at_utc": now,
        "updated_at_utc": now,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--playbook", type=Path, required=True)
    parser.add_argument("--deltas", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--family", required=True)
    parser.add_argument("--mode", default="pgmr_lite")
    parser.add_argument("--max-new-rules", type=int, default=5)
    args = parser.parse_args()

    playbook = load_json(args.playbook)
    deltas = load_json(args.deltas)

    if not isinstance(deltas, list):
        raise ValueError("Deltas must be a JSON array.")

    now = datetime.now(timezone.utc).isoformat()

    existing_keys = set()
    existing_ids = set()

    for b in playbook.get("bullets", []):
        existing_ids.add(b.get("id"))
        existing_keys.add((norm(b.get("title", "")), norm(b.get("content", ""))))

    accepted = []
    rejected = []

    for rule in deltas:
        title = str(rule.get("title", "")).strip()
        content = str(rule.get("content", "")).strip()

        if not title or not content:
            rejected.append((title, "missing title/content"))
            continue

        if rule.get("family") and rule.get("family") != args.family:
            rejected.append((title, "wrong family"))
            continue

        if rule.get("mode") and rule.get("mode") != args.mode:
            rejected.append((title, "wrong mode"))
            continue

        if is_generic(rule):
            rejected.append((title, "generic rule"))
            continue

        if args.mode == "pgmr_lite" and contains_direct_orkg(rule):
            rejected.append((title, "direct ORKG IDs in pgmr_lite rule"))
            continue

        key = (norm(title), norm(content))
        if key in existing_keys:
            rejected.append((title, "duplicate existing rule"))
            continue

        bullet = as_bullet(rule, args.family, args.mode, now)

        if bullet["id"] in existing_ids:
            rejected.append((title, "duplicate stable id"))
            continue

        accepted.append(bullet)
        existing_keys.add(key)
        existing_ids.add(bullet["id"])

        if len(accepted) >= args.max_new_rules:
            break

    playbook.setdefault("bullets", []).extend(accepted)
    playbook["updated_at_utc"] = now
    playbook.setdefault("metadata", {})
    playbook["metadata"]["last_llm_import_at_utc"] = now

    output = args.output or args.playbook
    write_json(output, playbook)

    print("playbook:", args.playbook)
    print("deltas:", args.deltas)
    print("accepted:", len(accepted))
    for b in accepted:
        print("  +", b["priority"], b["title"])

    print("rejected:", len(rejected))
    for title, reason in rejected:
        print("  -", title, "|", reason)

    print("output:", output)


if __name__ == "__main__":
    main()
