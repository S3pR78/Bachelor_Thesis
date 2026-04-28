/home/s3pr/UNI/BT/code/outputs/evaluation_runs/gpt_5_4/empire_compass__test__20260428_163956/benchmark_raw.json

/home/s3pr/UNI/BT/code/outputs/evaluation_runs/mistral_7b_instruct/empire_compass__test__20260428_155435/benchmark_summary.json

/home/s3pr/UNI/BT/code/outputs/evaluation_runs/qwen25_coder_7b_instruct/empire_compass__test__20260428_154005/benchmark_summary.json

/home/s3pr/UNI/BT/code/outputs/evaluation_runs/t5_base/empire_compass_mini__test__20260428_160646/benchmark_summary.json

# comments: 
Direkte SPARQL-Generierung funktioniert bei großen Modellen syntaktisch teilweise gut,
aber kleine Modelle wie T5-base scheitern bereits an ausführbarer Query-Struktur.
Auch lokale 7B-Modelle erzeugen zwar oft syntaktisch extrahierbare Queries,
haben aber weiterhin deutliche semantische und KG-Referenz-Probleme.
Deshalb ist ein Zwischenrepräsentationsansatz wie PGMR-lite sinnvoll,
weil er die schwierige Aufgabe trennt:
1. Modell erzeugt Query-Struktur.
2. Deterministischer Restore/Mappingsystem setzt echte ORKG-IDs ein.

The initial direct Text-to-SPARQL benchmark shows a clear gap between large proprietary models and smaller open-source models. GPT-5.4 with the full Empire-Compass prompt achieved perfect query extraction and a high execution rate, indicating that the prompt contains enough information for strong models to generate syntactically valid ORKG SPARQL queries. Among the open-source models, Qwen2.5-Coder-7B performed best, reaching full query extraction and a high execution success rate, but still remained clearly below the GPT baseline in answer-level metrics. Mistral-7B produced extractable queries in most cases, but its lower execution rate suggests difficulties with ORKG-specific predicates, classes, and query patterns.

T5-base, even with a shortened Empire-Compass-mini prompt, failed to generate executable SPARQL queries. Although some outputs could be extracted and the query form was often recognized, the execution success and structural F1 were zero. This indicates that direct ORKG SPARQL generation is too difficult for small sequence-to-sequence models under limited prompt length. These findings motivate the PGMR-lite approach, which separates query-structure generation from the deterministic restoration of ORKG-specific identifiers.