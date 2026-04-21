# Data Directory

This directory contains the project data used throughout dataset construction, review, validation, analysis, and final export.

## Purpose

The `code/data/` directory is the central location for:
- source benchmark data
- dataset expansion artifacts
- working dataset files
- reports and analyses
- final dataset exports
- archived intermediate or historical data

The goal of this structure is to separate:
- active working files
- reusable source data
- generated expansion material
- final outputs
- archived historical artifacts

## Main structure

- `dataset/`
  Main dataset workspace. This is the most important subdirectory for benchmark and training data preparation.

## Working principle

In general:
- active dataset work should happen inside `code/data/dataset/working/`
- final exports should be stored inside `code/data/dataset/final/`
- reports should be stored inside `code/data/dataset/reports/`
- historical or outdated but still reproducible artifacts should be stored inside `code/data/dataset/archive/`

## Notes

This directory has gone through several iterations during development.
Some older files and structures are kept for reproducibility, but the current active workflow should always be documented in the relevant README files inside `dataset/`.