# Core Source Package

This package contains core integration utilities for model loading and provider access.

## Modules

- `download_manager.py`
  - Handles downloading and caching of model files or data.
- `model_loader.py`
  - Loads model weights and config for local model execution.
- `openai_provider.py`
  - Provides an OpenAI interface for prompt-based generation.

## Usage

These modules are used by higher-level pipeline components to abstract model and API details.
