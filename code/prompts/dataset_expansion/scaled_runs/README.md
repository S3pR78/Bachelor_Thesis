# Scaled Runs

This directory contains wave-based run prompts for large-scale candidate generation.

Unlike `part1` and `part2`, which belong to the controlled core expansion layer, the files here are intended for scaled fine-tuning candidate generation.

## Purpose

Use scaled runs to generate many more candidate entries after the core batch logic has been validated.

## Naming convention

Pattern:
- `<batch>_<family>_waveXX.md`

Examples:
- `b001_nlp4re_wave01.md`
- `b002_empirical_wave02.md`
- `b004_nlp4re_wave05.md`

## Important rule

Scaled runs must still:
- use the correct family base prompt
- use the correct wrapper prompt
- avoid duplicates against previous waves and core runs
- remain candidate data until validation