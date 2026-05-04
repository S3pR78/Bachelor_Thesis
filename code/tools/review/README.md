# Review Tools

This folder contains scripts for reviewing, checking, and selecting candidate examples produced during dataset expansion.

## Scripts

- `benchmark_summary_app.py`
  - Launch an interactive Streamlit app for benchmark summaries and inspection.
- `check_expansion_candidates.py`
  - Perform automatic checks on generated expansion candidates.
- `review_expansion_candidates.py`
  - Review candidate examples manually or with guided heuristics.
- `select_green_candidates.py`
  - Select high-quality "green" candidates for inclusion in the dataset.

## Usage

These scripts support the human review and selection stage of the dataset pipeline. Run them from the repository root with `PYTHONPATH=code`.
