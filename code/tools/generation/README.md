# Generation Tools

This folder contains scripts for generating new dataset candidates and running prompt-based expansion.

## Scripts

- `assemble_expansion_prompt.py`
  - Assemble prompt templates and inputs for dataset expansion tasks.
- `run_expansion_prompt_openai.py`
  - Execute the expansion prompt with OpenAI and collect generated candidates.

## Usage

These tools are used during dataset expansion. Run them from the repository root with:

```bash
PYTHONPATH=code python code/tools/generation/run_expansion_prompt_openai.py
```
