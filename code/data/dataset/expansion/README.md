# Dataset Expansion Workspace

This directory contains the data expansion workflow for benchmark and training candidate generation.

## Purpose

The `expansion/` directory is used for generating, reviewing, selecting, and repairing candidate dataset entries before they are incorporated into the main dataset working pool.

It is the main workspace for expansion-specific artifacts, not the final benchmark dataset itself.

## Subdirectories

### `candidates/`
Generated candidate files produced from assembled prompts.

Typical contents:
- batch outputs
- wave outputs
- candidate JSON files before final consolidation

These files are generation outputs and should not automatically be treated as benchmark-ready.

### `review/`
Review outputs for generated candidates.

Typical contents:
- execution review files
- validation-oriented review outputs
- other review artifacts used to assess candidate quality

This directory is used to determine whether generated entries are usable, weak, or problematic.

### `selected/`
Selected candidate pools derived from review results.

Typical contents:
- merged green candidate pool
- merged yellow candidate pool
- selection summaries
- enriched or filtered selection files

This directory is an important bridge between expansion and the main dataset workflow.

### `repair/`
Repair-oriented files for problematic or questionable entries.

Use this directory for:
- repair candidates
- manual or semi-automatic query fixes
- repair dictionaries
- repair experiments

Only keep repair-related artifacts here.

## Top-level files

Top-level files in `expansion/` should be limited to documentation and planning artifacts, such as:
- methodology notes
- generation plans
- batch planning files
- expansion matrices

Examples:
- expansion plans
- methodology writeups
- batch definitions

These files document how expansion was designed, but they are not active dataset working files themselves.

## Recommended workflow

The intended workflow is:

1. generate candidate files into `candidates/`
2. review them in `review/`
3. merge or separate usable subsets in `selected/`
4. repair difficult cases in `repair/` if needed
5. move final validated working data into `../working/`

## Important distinction

This directory is for expansion-stage processing.

It should not become the location of:
- the final benchmark dataset
- the final training dataset
- the long-term main source of truth

Once candidate pools are sufficiently cleaned, reviewed, deduplicated, and validated, the active master dataset should live in `../working/`.

## Cleanup rule

Inside this directory:
- keep files that are still relevant to the expansion workflow
- archive or remove obsolete batch artifacts once they are clearly superseded
- avoid mixing final dataset exports into this workspace