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