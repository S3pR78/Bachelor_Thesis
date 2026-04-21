# Dataset Workspace

This directory contains the main dataset pipeline outputs and supporting data used for benchmark construction, training preparation, review, and final export.

## Directory overview

### `sources/`
Original or source-aligned dataset material.

Use this directory for:
- original benchmark examples
- manually curated source datasets
- source-family-specific merged seed files

This directory should contain data that acts as an input source for later processing steps, not the newest working dataset.

### `expansion/`
Dataset expansion workspace.

This directory contains expansion-related artifacts such as:
- generated candidates
- execution reviews
- selection pools
- repair material
- expansion plans and methodology notes

This is the main area for question/query generation and review before entries enter the main validated working pool.

### `working/`
Current active dataset working files.

This is the most important directory during dataset construction.
Use it for files that are currently being edited, reviewed, enriched, deduplicated, or prepared for splitting.

Examples:
- current validated master dataset
- manually reviewed working files
- split-preparation files

If you are unsure where active work should happen, start here.

### `reports/`
Reports, summaries, and analysis outputs.

Use this directory for:
- deduplication reports
- field distribution reports
- validation reports
- selection summaries
- split statistics

This directory should contain diagnostics and analysis outputs, not primary working datasets.

### `final/`
Final exported datasets.

Use this directory for finalized outputs such as:
- benchmark test set
- validation set
- training set
- training extended set
- final benchmark-ready files used in experiments

Only stable, intentionally exported dataset files should be stored here.

### `archive/`
Historical and inactive artifacts kept for reproducibility.

Use this directory for:
- old merged datasets
- outdated intermediate files
- older benchmark versions
- historical working snapshots no longer part of the active workflow

Files here should not be treated as the current source of truth.

## Recommended workflow

The intended high-level workflow is:

1. start from `sources/` and `expansion/`
2. review and consolidate entries
3. move the active master pool into `working/`
4. generate reports in `reports/`
5. export finalized splits into `final/`
6. move superseded or obsolete intermediate material into `archive/`

## Source of truth

At any given time, there should be a clearly identified current master working dataset inside `working/`.

For example:
- `working/master_validated_working.json`

This file should be treated as the main basis for:
- distribution analysis
- split design
- final export

## Notes on benchmark quality

Not all reviewed material has the same purpose.

Typical distinction:
- stronger reviewed items may be used for benchmark/test or validation
- weaker but still useful items may be retained for training or reserve use

This distinction should be reflected later in split strategy and final export decisions, not by mixing all files indiscriminately.