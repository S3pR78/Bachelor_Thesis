# Dataset Expansion Prompts

## Current active workflow

1. Assemble the final prompt from:
   - a family base prompt
   - a batch wrapper
   - a run file

2. Generate a minimal candidate JSON output with only:
   - `id`
   - `question`
   - `gold_sparql`
   - `family`
   - `answer_type`

3. Run review checks on generated candidates, including:
   - duplicate and near-duplicate checks
   - schema-faithfulness checks
   - lightweight execution review against the SPARQL endpoint

4. Flag suspicious or repairable entries for later review.

5. Enrich additional metadata only in a later step, after review and filtering.

## Active prompt path

The active generation workflow uses:
- `wrappers/`
- `runs/`
- `scaled_runs/`
- `assemble_expansion_prompt.py`

## Archive note

The `final/` directory is currently archival/reference only and is not the primary generation path.