# Online ACE Selected-Attempt Benchmark Run

- model: `qwen25_coder_7b_pgmr_qlora`
- prompt_mode: `pgmr`
- dataset: `code/data/dataset/pgmr/final/benchmark.json`
- online_mode: `test_time_repair`

This folder stores the selected final attempts from an Online ACE run in the standard evaluation run layout. `benchmark_raw.json` contains one selected raw result entry per benchmark item. `benchmark_summary.json` uses the normal benchmark summary structure. `selected_attempts.json` records which attempt was selected for each item.
