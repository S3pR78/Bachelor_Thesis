# SPARQL Package

`src/sparql/` contains shared SPARQL helpers for execution, prefix handling, query-form detection, and normalization.

## Modules

| Module | Purpose |
| --- | --- |
| `execution.py` | Executes SPARQL queries against a configured endpoint and detects query forms such as `SELECT` and `ASK`. |
| `prefixes.py` | Prepends ORKG/RDF/RDFS/XSD prefixes used throughout the project. |
| `normalization.py` | Normalizes SPARQL text for consistent storage, deduplication, and comparison. |

## Default Endpoint

Many scripts use the ORKG triplestore:

```text
https://www.orkg.org/triplestore
```

Endpoint-based tools require network access. If no endpoint is provided to evaluation, execution can be skipped while query extraction and text metrics still run.

## Used By

- dataset execution validation
- gold-result enrichment
- benchmark evaluation
- PGMR restoration/execution
- query normalization and deduplication
