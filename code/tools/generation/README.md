# Generation Tools

These tools assemble and run prompts for dataset expansion. They produce candidate question/SPARQL examples that must still be reviewed, validated, selected, and enriched before they become part of a working or final dataset.

## Scripts

| Script | Purpose |
| --- | --- |
| `assemble_expansion_prompt.py` | Combine a base prompt, wrapper prompt, and run prompt into one assembled prompt file. |
| `run_expansion_prompt_openai.py` | Send an assembled expansion prompt to OpenAI and write generated candidates plus metadata. |

## Prompt Inputs

Expansion prompt source files live under:

```text
code/prompts/dataset_expansion/
```

Important subdirectories:

- `wrappers/`: reusable generation objectives such as answer-type gaps, hard cases, or missing query components
- `runs/`: concrete smaller run definitions
- `scaled_runs/`: wave-based larger run definitions
- `assembled/`: generated full prompts ready for model execution

## Typical Workflow

1. Choose a wrapper and run file.
2. Assemble the full prompt.
3. Run the assembled prompt with OpenAI.
4. Save raw candidate JSON under `code/data/dataset/expansion/candidates/`.
5. Review candidates with `code/tools/review/`.

Example assembly:

```bash
PYTHONPATH=code python code/tools/generation/assemble_expansion_prompt.py \
  --base-prompt code/prompts/dataset_expansion/final/FINAL_PROMPT_TEMPLATE.md \
  --wrapper-prompt code/prompts/dataset_expansion/wrappers/b005_hard_case_buffer.md \
  --run-prompt code/prompts/dataset_expansion/scaled_runs/b005_nlp4re_wave01.md \
  --output-file code/prompts/dataset_expansion/assembled/b005_nlp4re_wave01_assembled.md
```

Example OpenAI run:

```bash
PYTHONPATH=code python code/tools/generation/run_expansion_prompt_openai.py \
  --id-prefix b005_nlp4re_w01 \
  --prompt-file code/prompts/dataset_expansion/assembled/b005_nlp4re_wave01_assembled.md \
  --output-file code/data/dataset/expansion/candidates/b005_nlp4re_wave01_candidates.json \
  --model gpt-5.4-mini
```

## Important Rule

Generated candidates are not benchmark-ready. Treat them as raw material until they pass review, execution validation, deduplication, and enrichment.
