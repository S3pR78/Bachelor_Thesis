# Dataset Expansion Prompts

This directory contains the prompt-building assets used for dataset expansion.

## Purpose

The prompt workflow in this directory is used to generate candidate benchmark/training entries for the supported template families.

The active workflow is based on:
1. a family-specific base prompt
2. a wrapper prompt
3. a run prompt or scaled run prompt
4. prompt assembly
5. model generation
6. execution review and later selection

## Active workflow

### 1. Base prompt
A family-specific base prompt provides the schema and template grounding.

Typical families:
- `nlp4re`
- `empirical_research_practice`

### 2. Wrapper prompt
A wrapper prompt defines the batch objective or generation strategy, for example:
- answer-type expansion
- missing query components
- non-factoid reasoning
- hard-case reserve generation
- NLP4RE-priority generation

### 3. Run prompt
A run prompt defines the concrete generation request, such as:
- batch id
- wave id
- expected count
- family
- generation focus

### 4. Assembly
The final generation prompt is assembled from:
- base prompt
- wrapper prompt
- run/scaled run prompt

### 5. Generation output format
The active generation format is intentionally minimal.

Generated candidate entries should contain only:
- `id` or later-assigned deterministic id, depending on the current generation tool version
- `question`
- `gold_sparql`
- `family`
- `answer_type`

Additional metadata is not generated directly in the prompt anymore.
It is added later during enrichment and review.

### 6. Review and selection
After generation, candidates are reviewed in the data pipeline:
- execution review
- green/yellow/red selection
- normalization
- deduplication
- manual review
- later schema-aligned enrichment

## Directory structure

### `wrappers/`
Reusable wrapper prompts that define the high-level purpose of a generation batch.

Examples:
- answer-type coverage
- hard-case buffer
- missing query components
- family-priority prompts

### `runs/`
Concrete non-scaled run prompts for smaller or earlier batch generation.

These are mostly useful for:
- initial generation
- small controlled batches
- historical comparison
- reproducibility

### `scaled_runs/`
Wave-based prompts for larger generation runs.

Use this directory for:
- scaled candidate generation
- wave-based expansion
- later large-batch runs such as `wave01`, `wave02`, etc.

This is the main area for large-scale generation.

### `assembled/`
Fully assembled prompts ready for model execution.

These files are generated artifacts, not hand-authored source prompts.
They may be regenerated from:
- base prompt
- wrapper prompt
- run/scaled run prompt

### `final/`
Archival/reference-only prompt artifacts.

This directory is not part of the main active generation path.
Keep it only for historical reference, reproducibility, or comparison with earlier workflows.

## Recommended usage

For new generation work:
- edit `wrappers/` only when the generation strategy changes
- edit `runs/` or `scaled_runs/` for concrete batch execution
- regenerate `assembled/` prompts through the assembly tool
- do not manually treat `assembled/` files as the primary source of truth

## Important distinction

Source prompt logic should live in:
- `wrappers/`
- `runs/`
- `scaled_runs/`

Generated prompt artifacts should live in:
- `assembled/`

Historical prompt outputs should live in:
- `final/`

## Cleanup rule

If prompt files are no longer part of the active generation workflow:
- keep them only if they are useful for reproducibility
- otherwise archive or remove them
- avoid leaving outdated run prompts mixed with currently active ones

## Notes

This prompt directory has evolved over multiple iterations.
The current workflow prefers:
- minimal generation output
- later metadata enrichment
- review-driven selection
- deterministic post-processing where possible