# ACE Source Package

This package contains ACE pipeline logic, playbook handling, and reflection utilities.

## Modules

- `curator.py`
  - Curates playbooks and dataset examples for ACE workflows.
- `llm_pipeline.py`
  - Runs the LLM pipeline for ACE tasks.
- `llm_reflector.py`
  - Implements reflection-based LLM reruns and feedback loops.
- `offline_loop.py`
  - Supports offline execution and debugging of the ACE pipeline.
- `playbook.py`
  - Defines playbook structures and serialization.
- `reflector.py`
  - Provides reflection strategies for improving candidate generation.
- `rendering.py`
  - Renders playbook data or model outputs for review.
- `routing.py`
  - Routes tasks and decisions inside the ACE pipeline.
- `traces.py`
  - Captures and analyzes debug traces and execution history.

## Usage

This package is primarily imported by higher-level scripts and tools in the project.
