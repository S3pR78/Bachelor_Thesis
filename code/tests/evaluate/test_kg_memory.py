from __future__ import annotations

from pathlib import Path

import pytest

from src.evaluate.kg_memory import (
    extract_orkg_refs_from_text,
    get_allowed_orkg_ref_counts,
    load_allowed_orkg_refs,
)


def test_extracts_prefixed_refs_from_json_like_text() -> None:
    text = """
    {
      "canonical_uri": "orkgp:P181003",
      "template_class": "orkgc:C121001",
      "template_resource": "orkgr:R1544125"
    }
    """

    refs = extract_orkg_refs_from_text(text)

    assert refs == frozenset(
        {
            "orkgp:P181003",
            "orkgc:C121001",
            "orkgr:R1544125",
        }
    )


def test_extracts_full_iris_as_canonical_refs() -> None:
    text = """
    {
      "predicate": "http://orkg.org/orkg/predicate/P181003",
      "class": "https://orkg.org/orkg/class/C121001",
      "resource": "https://www.orkg.org/orkg/resource/R1544125"
    }
    """

    refs = extract_orkg_refs_from_text(text)

    assert refs == frozenset(
        {
            "orkgp:P181003",
            "orkgc:C121001",
            "orkgr:R1544125",
        }
    )


def test_extracts_special_predicates() -> None:
    text = """
    {
      "canonical_uri": "orkgp:HAS_EVALUATION"
    }
    """

    refs = extract_orkg_refs_from_text(text)

    assert refs == frozenset({"orkgp:HAS_EVALUATION"})


def test_invalid_text_type_raises_value_error() -> None:
    with pytest.raises(ValueError):
        extract_orkg_refs_from_text(123)  # type: ignore[arg-type]


def test_load_allowed_orkg_refs_from_directory(tmp_path: Path) -> None:
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()

    (memory_dir / "nlp4re_memory.json").write_text(
        """
        {
          "items": [
            {"canonical_uri": "orkgp:P31"},
            {"canonical_uri": "orkgp:P181003"},
            {"canonical_uri": "orkgc:C121001"}
          ]
        }
        """,
        encoding="utf-8",
    )

    (memory_dir / "empirical_memory.json").write_text(
        """
        {
          "items": [
            {"canonical_uri": "orkgp:P29"},
            {"canonical_uri": "orkgc:C27001"},
            {"canonical_uri": "orkgr:R186491"}
          ]
        }
        """,
        encoding="utf-8",
    )

    result = load_allowed_orkg_refs(memory_dir)

    assert result["predicate_refs"] == frozenset(
        {
            "orkgp:P31",
            "orkgp:P181003",
            "orkgp:P29",
        }
    )
    assert result["class_refs"] == frozenset(
        {
            "orkgc:C121001",
            "orkgc:C27001",
        }
    )
    assert result["resource_refs"] == frozenset({"orkgr:R186491"})
    assert result["all_refs"] == frozenset(
        {
            "orkgp:P31",
            "orkgp:P181003",
            "orkgp:P29",
            "orkgc:C121001",
            "orkgc:C27001",
            "orkgr:R186491",
        }
    )
    assert result["scanned_file_count"] == 2


def test_load_allowed_orkg_refs_from_multiple_paths(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    first.write_text('{"canonical_uri": "orkgp:P181003"}', encoding="utf-8")
    second.write_text('{"canonical_uri": "orkgc:C121001"}', encoding="utf-8")

    result = load_allowed_orkg_refs([first, second])

    assert result["predicate_refs"] == frozenset({"orkgp:P181003"})
    assert result["class_refs"] == frozenset({"orkgc:C121001"})
    assert result["scanned_file_count"] == 2


def test_missing_memory_path_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        load_allowed_orkg_refs("does/not/exist")


def test_get_allowed_orkg_ref_counts(tmp_path: Path) -> None:
    memory_file = tmp_path / "memory.json"
    memory_file.write_text(
        """
        {
          "predicate": "orkgp:P31",
          "class": "orkgc:C121001",
          "resource": "orkgr:R1544125"
        }
        """,
        encoding="utf-8",
    )

    counts = get_allowed_orkg_ref_counts(memory_file)

    assert counts == {
        "predicate_ref_count": 1,
        "class_ref_count": 1,
        "resource_ref_count": 1,
        "all_ref_count": 3,
        "scanned_file_count": 1,
    }
