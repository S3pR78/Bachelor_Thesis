# Archived Dataset Artifacts

This directory stores historical, superseded, or inactive dataset files that are kept for reproducibility.

## Purpose

Use this directory for files that should no longer be treated as active working data, but are still worth preserving, for example:
- old merged benchmark versions
- outdated intermediate files
- historical snapshots of master pools
- earlier enriched dataset versions
- retired working files that were replaced by newer versions

## Important rule

Files in this directory are not the current source of truth.

Do not use archived files as the default input for:
- active editing
- distribution analysis
- split design
- final export

Instead, use files from:
- `../working/` for active work
- `../final/` for final outputs

## Why archive instead of delete

Archived files are kept to support:
- reproducibility
- traceability of earlier processing steps
- recovery of older dataset states if needed
- thesis documentation and project history

## Suggested internal organization

If this directory becomes large, it is reasonable to create subfolders such as:
- `benchmark_v1/`
- `master_pool/`
- `old_exports/`
- `historical_reports/`

## Notes

Archiving is preferred over keeping outdated files mixed into active directories.
The goal is to reduce clutter in the active workflow while preserving important historical artifacts.