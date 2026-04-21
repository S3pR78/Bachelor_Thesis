# Working Dataset Files

This directory contains the current active dataset files used during dataset preparation.

## Purpose

Use this directory for files that are still part of the active workflow, such as:
- the current validated master dataset
- manually reviewed working files
- pre-split dataset versions
- files currently being enriched or prepared for final export

This directory should contain the current source of truth for ongoing dataset work.

## Recommended usage

Typical files in this directory may include:
- `master_validated_working.json`
- split-preparation files
- manually revised benchmark-ready working files

When performing:
- distribution analysis
- split planning
- final dataset preparation

the input should normally come from this directory.

## Important rule

Only keep currently active working files here.

If a file is:
- outdated
- superseded
- only needed for reproducibility
- an intermediate snapshot no longer used

it should be moved to `../archive/` instead of staying here.

## Notes

This directory is intentionally separate from:
- `../sources/` for source materials
- `../expansion/` for generation/review artifacts
- `../reports/` for analysis outputs
- `../final/` for final exported datasets