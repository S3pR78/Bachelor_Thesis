import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("code/data/ace_playbooks")

MODELS = [
    "t5_base_pgmr_mini_15ep",
    "qwen25_coder_7b_pgmr_mini_qlora",
    "mistral_7b_pgmr_mini_qlora",
]

FAMILY = "nlp4re"
NOW = datetime.now(timezone.utc).isoformat()


# Diese Regeln sind im Basis-Prompt schon enthalten oder redundant.
DISABLE_IDS_CONTAINING = [
    "global_any_output_format_initial",
    "no_extracted_query",
    "pgmr_format_initial",
]


def update_bullet(b: dict, *, priority: int | None = None, enabled: bool | None = None, reason: str | None = None) -> None:
    if priority is not None:
        b["priority"] = priority
    if enabled is not None:
        b["enabled"] = enabled
    if reason:
        b["curation_note"] = reason
    b["updated_at_utc"] = NOW


def reprioritize(path: Path, model: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    bullets = data.get("bullets", [])

    for b in bullets:
        bid = b.get("id", "")
        title = b.get("title", "")
        category = b.get("category", "")

        # Redundante Output-/Format-Regeln deaktivieren.
        if any(x in bid for x in DISABLE_IDS_CONTAINING):
            update_bullet(
                b,
                enabled=False,
                reason="Disabled because the base PGMR-mini prompt already contains this generic output/format instruction.",
            )
            continue

        # Modell-spezifische Prioritäten.
        if model == "t5_base_pgmr_mini_15ep":
            if category == "pgmr_unmapped_placeholders":
                update_bullet(
                    b,
                    priority=120,
                    enabled=True,
                    reason="High priority for T5 because it often invents unknown PGMR placeholders.",
                )
            elif category == "contribution_pattern":
                update_bullet(
                    b,
                    priority=115,
                    enabled=True,
                    reason="High priority structural rule for valid NLP4RE PGMR-lite.",
                )
            elif category == "query_form_mismatch":
                update_bullet(b, priority=110, enabled=True)
            elif category == "predicate_ref_mismatch":
                update_bullet(b, priority=108, enabled=True)
            elif category == "answer_mismatch":
                update_bullet(b, priority=106, enabled=True)
            elif category == "pgmr_restore_error":
                update_bullet(b, priority=95, enabled=True)
            elif category in {"prediction_execution_error", "endpoint_bad_request"}:
                update_bullet(b, priority=90, enabled=True)

        else:
            # Qwen/Mistral: weniger generisch, mehr Struktur.
            if category == "contribution_pattern":
                update_bullet(
                    b,
                    priority=120,
                    enabled=True,
                    reason="Highest priority because structural contribution binding is central for NLP4RE.",
                )
            elif category == "predicate_ref_mismatch":
                update_bullet(
                    b,
                    priority=115,
                    enabled=True,
                    reason="Prioritize concrete predicate-role corrections over generic output rules.",
                )
            elif category == "answer_mismatch":
                update_bullet(
                    b,
                    priority=112,
                    enabled=True,
                    reason="Prioritize semantic constraints over generic format rules.",
                )
            elif category == "query_form_mismatch":
                update_bullet(b, priority=110, enabled=True)
            elif category == "pgmr_unmapped_placeholders":
                update_bullet(
                    b,
                    priority=100,
                    enabled=True,
                    reason="Keep placeholder control, but below structural rules for larger models.",
                )
            elif category == "pgmr_restore_error":
                update_bullet(b, priority=95, enabled=True)
            elif category in {"prediction_execution_error", "endpoint_bad_request"}:
                update_bullet(b, priority=90, enabled=True)
            elif category == "endpoint_uri_too_long":
                update_bullet(b, priority=80, enabled=True)

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("updated", path)


def main() -> None:
    for model in MODELS:
        path = ROOT / model / f"{FAMILY}_pgmr_lite_playbook.json"
        if not path.exists():
            print("missing", path)
            continue
        reprioritize(path, model)


if __name__ == "__main__":
    main()