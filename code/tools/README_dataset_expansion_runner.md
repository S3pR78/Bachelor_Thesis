# Dataset Expansion Runner

This document explains how to run the OpenAI-based dataset expansion workflow for candidate generation.

## Tool

The runner script is:

- `code/tools/run_expansion_prompt_openai.py`

It reads a fully assembled prompt file, sends it to the OpenAI API, validates the returned JSON array, and writes the generated candidate entries to a JSON file.

## Requirements

Before running the script, make sure:

- your Python environment is active
- the `openai` package is installed
- `OPENAI_API_KEY` is set in your environment

Example:

```bash
export OPENAI_API_KEY="your_api_key_here"