from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from src.evaluate.dataset_loader import load_evaluate_entries


def load_schema_definition(schema_path: str | Path) -> dict[str, Any]:
    """
    Load a schema JSON file and return it as a dictionary.
    """
    path = Path(schema_path)

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Schema file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        schema = json.load(f)

    if not isinstance(schema, dict):
        raise ValueError("Schema JSON must be a dictionary/object at the top level.")

    return schema


def load_analysis_inputs(
    dataset_path: str | Path,
    schema_path: str | Path | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """
    Load dataset entries and optionally a schema definition for later analysis.
    """
    dataset_path = Path(dataset_path)

    entries = load_evaluate_entries(str(dataset_path), limit=limit)
    schema = load_schema_definition(schema_path) if schema_path is not None else None

    return {
        "dataset_path": str(dataset_path),
        "dataset_name": dataset_path.stem,
        "entries": entries,
        "entry_count": len(entries),
        "schema_path": str(schema_path) if schema_path is not None else None,
        "schema": schema,
        "has_schema": schema is not None,
    }


def collect_available_fields(entries: list[dict]) -> list[str]:
    """
    Collect all field names that appear in dictionary entries.
    """
    field_names: set[str] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        field_names.update(entry.keys())

    return sorted(field_names)


def build_field_presence_summary(entries: list[dict]) -> dict[str, Any]:
    """
    Build a summary of which fields appear across dataset entries.
    """
    dict_entries = [entry for entry in entries if isinstance(entry, dict)]
    total_entries = len(dict_entries)

    field_counter: Counter[str] = Counter()

    for entry in dict_entries:
        field_counter.update(entry.keys())

    all_fields = sorted(field_counter.keys())

    field_details = {}
    for field_name in all_fields:
        present_count = field_counter[field_name]
        field_details[field_name] = {
            "present_count": present_count,
            "missing_count": total_entries - present_count,
            "coverage_ratio": round(present_count / total_entries, 4) if total_entries > 0 else None,
        }

    return {
        "total_entries": total_entries,
        "field_count": len(all_fields),
        "fields": all_fields,
        "field_details": field_details,
    }



def extract_schema_field_names(schema: dict[str, Any]) -> list[str]:
    """
    Extract top-level field names from the schema's 'properties' object.
    """
    if not isinstance(schema, dict):
        raise ValueError("Schema must be a dictionary/object.")

    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise ValueError(
            "Schema must contain a top-level 'properties' dictionary."
        )

    return sorted(properties.keys())


def extract_required_schema_fields(schema: dict[str, Any]) -> list[str]:
    """
    Extract required top-level field names from the schema.
    """
    if not isinstance(schema, dict):
        raise ValueError("Schema must be a dictionary/object.")

    required_fields = schema.get("required", [])
    if not isinstance(required_fields, list):
        raise ValueError("Schema field 'required' must be a list.")

    return sorted(field for field in required_fields if isinstance(field, str))


def build_schema_field_comparison(
    entries: list[dict],
    schema: dict[str, Any],
) -> dict[str, Any]:
    """
    Compare dataset fields against schema-defined top-level fields.
    """
    dataset_fields = set(collect_available_fields(entries))
    schema_fields = set(extract_schema_field_names(schema))
    required_fields = set(extract_required_schema_fields(schema))

    shared_fields = sorted(dataset_fields & schema_fields)
    schema_only_fields = sorted(schema_fields - dataset_fields)
    dataset_only_fields = sorted(dataset_fields - schema_fields)
    missing_required_fields = sorted(required_fields - dataset_fields)

    return {
        "dataset_field_count": len(dataset_fields),
        "schema_field_count": len(schema_fields),
        "required_field_count": len(required_fields),
        "shared_field_count": len(shared_fields),
        "shared_fields": shared_fields,
        "schema_only_field_count": len(schema_only_fields),
        "schema_only_fields": schema_only_fields,
        "dataset_only_field_count": len(dataset_only_fields),
        "dataset_only_fields": dataset_only_fields,
        "missing_required_field_count": len(missing_required_fields),
        "missing_required_fields": missing_required_fields,
    }




def is_missing_required_value(value: Any) -> bool:
    """
    Decide whether a required field value should count as missing.
    """
    if value is None:
        return True

    if isinstance(value, str) and not value.strip():
        return True

    if isinstance(value, list) and len(value) == 0:
        return True

    return False


def build_required_field_validation(
    entries: list[dict],
    schema: dict[str, Any],
) -> dict[str, Any]:
    """
    Validate required top-level schema fields for each dataset entry.
    """
    required_fields = extract_required_schema_fields(schema)

    missing_counts_by_field = {field_name: 0 for field_name in required_fields}
    entries_with_missing_required = []

    checked_entries = 0

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue

        checked_entries += 1
        missing_fields = []

        for field_name in required_fields:
            if field_name not in entry or is_missing_required_value(entry.get(field_name)):
                missing_fields.append(field_name)
                missing_counts_by_field[field_name] += 1

        if missing_fields:
            entries_with_missing_required.append(
                {
                    "entry_index": index,
                    "entry_id": entry.get("id", f"row_{index}"),
                    "missing_required_fields": missing_fields,
                }
            )

    invalid_entry_count = len(entries_with_missing_required)
    valid_entry_count = checked_entries - invalid_entry_count

    return {
        "checked_entry_count": checked_entries,
        "required_fields": required_fields,
        "valid_entry_count": valid_entry_count,
        "invalid_entry_count": invalid_entry_count,
        "missing_counts_by_field": missing_counts_by_field,
        "entries_with_missing_required": entries_with_missing_required,
    }



def schema_type_matches_value(expected_type: str, value: Any) -> bool:
    """
    Check whether a Python value matches a simple JSON-schema type.
    """
    if expected_type == "string":
        return isinstance(value, str)

    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)

    if expected_type == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)

    if expected_type == "boolean":
        return isinstance(value, bool)

    if expected_type == "array":
        return isinstance(value, list)

    if expected_type == "object":
        return isinstance(value, dict)

    if expected_type == "null":
        return value is None

    return True


def build_type_and_enum_validation(
    entries: list[dict],
    schema: dict[str, Any],
) -> dict[str, Any]:
    """
    Validate top-level field types and enum values against schema properties.
    Missing values are skipped here because required-field validation handles them separately.
    """
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("Schema must contain a top-level 'properties' dictionary.")

    checked_entries = 0
    invalid_entry_count = 0
    type_error_count = 0
    enum_error_count = 0
    entries_with_field_errors = []

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue

        checked_entries += 1
        field_errors = []

        for field_name, field_schema in properties.items():
            if not isinstance(field_schema, dict):
                continue

            if field_name not in entry:
                continue

            value = entry.get(field_name)

            if is_missing_required_value(value):
                continue

            expected_type = field_schema.get("type")
            if isinstance(expected_type, str):
                if not schema_type_matches_value(expected_type, value):
                    field_errors.append(
                        {
                            "field_name": field_name,
                            "error_type": "type_mismatch",
                            "expected_type": expected_type,
                            "actual_type": type(value).__name__,
                            "actual_value": value,
                        }
                    )
                    type_error_count += 1
                    continue

            allowed_values = field_schema.get("enum")
            if isinstance(allowed_values, list):
                if value not in allowed_values:
                    field_errors.append(
                        {
                            "field_name": field_name,
                            "error_type": "enum_mismatch",
                            "allowed_values": allowed_values,
                            "actual_value": value,
                        }
                    )
                    enum_error_count += 1

        if field_errors:
            invalid_entry_count += 1
            entries_with_field_errors.append(
                {
                    "entry_index": index,
                    "entry_id": entry.get("id", f"row_{index}"),
                    "field_errors": field_errors,
                }
            )

    valid_entry_count = checked_entries - invalid_entry_count

    return {
        "checked_entry_count": checked_entries,
        "valid_entry_count": valid_entry_count,
        "invalid_entry_count": invalid_entry_count,
        "type_error_count": type_error_count,
        "enum_error_count": enum_error_count,
        "entries_with_field_errors": entries_with_field_errors,
    }


def utc_now_iso() -> str:
    """
    Return the current UTC timestamp as an ISO string.
    """
    return datetime.now(timezone.utc).isoformat()


def build_dataset_analysis_report(
    dataset_path: str | Path,
    schema_path: str | Path | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """
    Build a combined dataset analysis report from dataset and optional schema.
    """
    inputs = load_analysis_inputs(
        dataset_path=dataset_path,
        schema_path=schema_path,
        limit=limit,
    )

    entries = inputs["entries"]
    schema = inputs["schema"]

    report = {
        "report_metadata": {
            "generated_at_utc": utc_now_iso(),
            "dataset_path": inputs["dataset_path"],
            "dataset_name": inputs["dataset_name"],
            "entry_count": inputs["entry_count"],
            "schema_path": inputs["schema_path"],
            "has_schema": inputs["has_schema"],
        },
        "field_presence": build_field_presence_summary(entries),
    }

    if schema is not None:
        report["schema_field_comparison"] = build_schema_field_comparison(
            entries,
            schema,
        )
        report["required_field_validation"] = build_required_field_validation(
            entries,
            schema,
        )
        report["type_and_enum_validation"] = build_type_and_enum_validation(
            entries,
            schema,
        )

    return report



def resolve_coverage_field_names(
    entries: list[dict],
    schema: dict[str, Any] | None = None,
    field_scope: str = "required",
) -> list[str]:
    """
    Resolve which field names should be used for coverage analysis.

    Supported field_scope values:
    - "required": only required schema fields
    - "schema": all top-level schema fields
    - "dataset": all fields found in dataset entries
    """
    if field_scope == "required":
        if schema is None:
            raise ValueError("Schema is required when field_scope='required'.")
        return extract_required_schema_fields(schema)

    if field_scope == "schema":
        if schema is None:
            raise ValueError("Schema is required when field_scope='schema'.")
        return extract_schema_field_names(schema)

    if field_scope == "dataset":
        return collect_available_fields(entries)

    raise ValueError(
        "field_scope must be one of: 'required', 'schema', 'dataset'."
    )


def build_field_coverage_summary(
    entries: list[dict],
    schema: dict[str, Any] | None = None,
    field_scope: str = "required",
) -> dict[str, Any]:
    """
    Build field-level coverage statistics with percentages.
    """
    field_names = resolve_coverage_field_names(
        entries=entries,
        schema=schema,
        field_scope=field_scope,
    )

    dict_entries = [entry for entry in entries if isinstance(entry, dict)]
    total_entries = len(dict_entries)

    field_details = {}

    for field_name in field_names:
        present_count = 0

        for entry in dict_entries:
            if field_name not in entry:
                continue

            if is_missing_required_value(entry.get(field_name)):
                continue

            present_count += 1

        missing_count = total_entries - present_count
        coverage_percent = (
            round((present_count / total_entries) * 100, 2)
            if total_entries > 0
            else None
        )

        field_details[field_name] = {
            "present_count": present_count,
            "missing_count": missing_count,
            "coverage_percent": coverage_percent,
        }

    return {
        "field_scope": field_scope,
        "total_entries": total_entries,
        "field_count": len(field_names),
        "fields": field_names,
        "field_details": field_details,
    }



def normalize_report_value_key(value: Any) -> str:
    """
    Convert a value into a stable string key for JSON reporting.
    """
    if isinstance(value, str):
        return value

    if value is None:
        return "null"

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (int, float)):
        return str(value)

    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def extract_enum_field_names(schema: dict[str, Any]) -> list[str]:
    """
    Extract top-level schema field names that define an enum.
    """
    if not isinstance(schema, dict):
        raise ValueError("Schema must be a dictionary/object.")

    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise ValueError(
            "Schema must contain a top-level 'properties' dictionary."
        )

    enum_field_names = []

    for field_name, field_schema in properties.items():
        if not isinstance(field_schema, dict):
            continue

        if isinstance(field_schema.get("enum"), list):
            enum_field_names.append(field_name)

    return sorted(enum_field_names)


def build_enum_distribution_summary(
    entries: list[dict],
    schema: dict[str, Any],
) -> dict[str, Any]:
    """
    Build distribution statistics for top-level enum fields in the schema.

    Percentages are calculated over valid enum values that are present.
    Unexpected values are reported separately.
    """
    if not isinstance(schema, dict):
        raise ValueError("Schema must be a dictionary/object.")

    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise ValueError(
            "Schema must contain a top-level 'properties' dictionary."
        )

    dict_entries = [entry for entry in entries if isinstance(entry, dict)]
    total_entries = len(dict_entries)
    enum_field_names = extract_enum_field_names(schema)

    field_details = {}

    for field_name in enum_field_names:
        field_schema = properties[field_name]
        allowed_values = field_schema.get("enum", [])

        allowed_value_counts = {
            normalize_report_value_key(value): 0
            for value in allowed_values
        }
        unexpected_value_counts: dict[str, int] = {}

        present_count = 0

        for entry in dict_entries:
            if field_name not in entry:
                continue

            value = entry.get(field_name)

            if is_missing_required_value(value):
                continue

            present_count += 1
            value_key = normalize_report_value_key(value)

            if value in allowed_values:
                allowed_value_counts[value_key] += 1
            else:
                unexpected_value_counts[value_key] = (
                    unexpected_value_counts.get(value_key, 0) + 1
                )

        valid_present_count = sum(allowed_value_counts.values())

        value_percents = {
            value_key: (
                round((count / valid_present_count) * 100, 2)
                if valid_present_count > 0
                else None
            )
            for value_key, count in allowed_value_counts.items()
        }

        missing_allowed_values = [
            value
            for value in allowed_values
            if allowed_value_counts[normalize_report_value_key(value)] == 0
        ]

        coverage_percent = (
            round((present_count / total_entries) * 100, 2)
            if total_entries > 0
            else None
        )

        field_details[field_name] = {
            "allowed_values": allowed_values,
            "allowed_value_count": len(allowed_values),
            "present_count": present_count,
            "missing_count": total_entries - present_count,
            "coverage_percent": coverage_percent,
            "valid_present_count": valid_present_count,
            "unexpected_value_count": sum(unexpected_value_counts.values()),
            "value_counts": allowed_value_counts,
            "value_percents": value_percents,
            "missing_allowed_values": missing_allowed_values,
            "unexpected_value_counts": unexpected_value_counts,
        }

    return {
        "total_entries": total_entries,
        "enum_field_count": len(enum_field_names),
        "enum_fields": enum_field_names,
        "field_details": field_details,
    }


def build_dataset_analysis_report(
    dataset_path: str | Path,
    schema_path: str | Path | None = None,
    limit: int | None = None,
    coverage_scopes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Build a combined dataset analysis report from dataset and optional schema.
    """
    inputs = load_analysis_inputs(
        dataset_path=dataset_path,
        schema_path=schema_path,
        limit=limit,
    )

    entries = inputs["entries"]
    schema = inputs["schema"]

    if coverage_scopes is None:
        coverage_scopes = ["required", "schema"]

    report = {
        "report_metadata": {
            "generated_at_utc": utc_now_iso(),
            "dataset_path": inputs["dataset_path"],
            "dataset_name": inputs["dataset_name"],
            "entry_count": inputs["entry_count"],
            "schema_path": inputs["schema_path"],
            "has_schema": inputs["has_schema"],
        },
        "field_presence": build_field_presence_summary(entries),
    }

    if schema is not None:
        report["schema_field_comparison"] = build_schema_field_comparison(
            entries,
            schema,
        )
        report["required_field_validation"] = build_required_field_validation(
            entries,
            schema,
        )
        report["type_and_enum_validation"] = build_type_and_enum_validation(
            entries,
            schema,
        )

        field_coverage = {}
        for field_scope in coverage_scopes:
            field_coverage[field_scope] = build_field_coverage_summary(
                entries=entries,
                schema=schema,
                field_scope=field_scope,
            )

        report["field_coverage"] = field_coverage
        report["enum_distributions"] = build_enum_distribution_summary(
            entries=entries,
            schema=schema,
        )

    return report