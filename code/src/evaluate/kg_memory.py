from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from src.evaluate.query_elements import (
    FULL_IRI_KIND_TO_PREFIX,
    FULL_ORKG_IRI_RE,
    PREFIXED_ORKG_REF_RE,
)


DEFAULT_MEMORY_FILE_SUFFIXES = {
    ".json",
    ".jsonl",
    ".md",
    ".txt",
    ".ttl",
    ".sparql",
}


def _empty_memory_result(
    *,
    source_paths: Iterable[Path],
    scanned_file_count: int = 0,
) -> dict:
    return {
        "predicate_refs": frozenset(),
        "class_refs": frozenset(),
        "resource_refs": frozenset(),
        "all_refs": frozenset(),
        "source_paths": tuple(str(path) for path in source_paths),
        "scanned_file_count": scanned_file_count,
    }


def _canonicalize_ref(prefix: str, local: str) -> str:
    return f"{prefix.lower()}:{local}"


def _split_refs_by_kind(refs: set[str]) -> dict[str, frozenset[str]]:
    predicate_refs = {ref for ref in refs if ref.startswith("orkgp:")}
    class_refs = {ref for ref in refs if ref.startswith("orkgc:")}
    resource_refs = {ref for ref in refs if ref.startswith("orkgr:")}

    return {
        "predicate_refs": frozenset(predicate_refs),
        "class_refs": frozenset(class_refs),
        "resource_refs": frozenset(resource_refs),
        "all_refs": frozenset(refs),
    }


def extract_orkg_refs_from_text(text: str | None) -> frozenset[str]:
    """Extract canonical ORKG refs from arbitrary text.

    Unlike query-element extraction for SPARQL, this function intentionally also
    scans string literals. This is needed for JSON memory files where ORKG refs
    occur as values such as "canonical_uri": "orkgp:P181003".
    """

    if text is None:
        return frozenset()

    if not isinstance(text, str):
        raise ValueError("text must be a string or None.")

    refs: set[str] = set()

    for match in PREFIXED_ORKG_REF_RE.finditer(text):
        refs.add(
            _canonicalize_ref(
                prefix=match.group("prefix"),
                local=match.group("local"),
            )
        )

    for match in FULL_ORKG_IRI_RE.finditer(text):
        kind = match.group("kind").lower()
        prefix = FULL_IRI_KIND_TO_PREFIX[kind]
        refs.add(
            _canonicalize_ref(
                prefix=prefix,
                local=match.group("local"),
            )
        )

    return frozenset(refs)


def _iter_memory_files(
    source_paths: Iterable[Path],
    *,
    allowed_suffixes: set[str],
) -> Iterable[Path]:
    for source_path in source_paths:
        if not source_path.exists():
            raise FileNotFoundError(f"Memory source path does not exist: {source_path}")

        if source_path.is_file():
            if source_path.suffix.lower() in allowed_suffixes:
                yield source_path
            continue

        for file_path in sorted(source_path.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() in allowed_suffixes:
                yield file_path


def load_allowed_orkg_refs(
    memory_paths: str | Path | Iterable[str | Path],
    *,
    allowed_suffixes: set[str] | None = None,
) -> dict:
    """Load allowed ORKG refs from one or more local memory paths.

    The function scans supported text-like files recursively and returns refs
    grouped by ORKG namespace:
    - orkgp:* as predicate_refs
    - orkgc:* as class_refs
    - orkgr:* as resource_refs
    """

    if isinstance(memory_paths, (str, Path)):
        source_paths = [Path(memory_paths)]
    else:
        source_paths = [Path(path) for path in memory_paths]

    if not source_paths:
        return _empty_memory_result(source_paths=[])

    suffixes = allowed_suffixes or DEFAULT_MEMORY_FILE_SUFFIXES

    all_refs: set[str] = set()
    scanned_file_count = 0

    for file_path in _iter_memory_files(source_paths, allowed_suffixes=suffixes):
        scanned_file_count += 1
        text = file_path.read_text(encoding="utf-8")
        all_refs.update(extract_orkg_refs_from_text(text))

    result = _split_refs_by_kind(all_refs)
    result["source_paths"] = tuple(str(path) for path in source_paths)
    result["scanned_file_count"] = scanned_file_count
    return result


def get_allowed_orkg_ref_counts(memory_paths: str | Path | Iterable[str | Path]) -> dict:
    memory = load_allowed_orkg_refs(memory_paths)

    return {
        "predicate_ref_count": len(memory["predicate_refs"]),
        "class_ref_count": len(memory["class_refs"]),
        "resource_ref_count": len(memory["resource_refs"]),
        "all_ref_count": len(memory["all_refs"]),
        "scanned_file_count": memory["scanned_file_count"],
    }
