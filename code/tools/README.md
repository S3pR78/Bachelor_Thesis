# Tools

Dieses Verzeichnis enthält Hilfsskripte für den Datensatz- und Benchmark-Workflow der Bachelorarbeit.

## Workflow-Phasen

### generation/
Skripte zum Erzeugen neuer Kandidaten:
- assemble_expansion_prompt.py
- run_expansion_prompt_openai.py

### review/
Skripte zur Prüfung und Selektion generierter Kandidaten:
- check_expansion_candidates.py
- review_expansion_candidates.py
- select_green_candidates.py

### dataset/
Skripte zur Nachbearbeitung und Anreicherung von Datensätzen:
- dedupe_dataset_entries.py
- normalize_sparql_in_dataset.py
- enrich_selected_candidates.py
- enrich_dataset_with_gold_results.py

### reporting/
Skripte zur Erstellung von Auswertungen und Berichten:
- export_dataset_validation_report.py
- export_dataset_field_distribution_report.py

### legacy/
Historische oder einmalige Skripte, die nicht mehr Teil des sauberen Hauptworkflows sind.

## Grundregel

Neue Tools sollen immer einer klaren Workflow-Phase zugeordnet werden und keine hartcodierten lokalen Pfade enthalten.