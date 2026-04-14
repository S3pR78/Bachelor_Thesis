import json
from pathlib import Path

def merge_json_files(input_files, output_file):
    merged_data = []
    
    # 1. Alle Dateien nacheinander einlesen
    for file_name in input_files:
        path = Path(file_name)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Falls die Datei eine Liste ist, hängen wir sie an die Gesamtliste an
                if isinstance(data, list):
                    merged_data.extend(data)
                else:
                    merged_data.append(data)
            print(f"Datei '{file_name}' geladen.")
        else:
            print(f"Warnung: Datei '{file_name}' wurde nicht gefunden.")

    # 2. Nur die source_id fortlaufend korrigieren
    # Wir fangen bei 1 an und gehen bis zum Ende der kombinierten Liste
    for index, item in enumerate(merged_data, start=1):
        # Wir setzen die source_id als String, passend zum ursprünglichen Format
        item['source_id'] = str(index)
        
        # 'id' bleibt hier völlig unverändert, wie von dir gewünscht.

    # 3. Ergebnis speichern
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nErfolg! {len(merged_data)} Einträge zusammengeführt.")
    print(f"Die 'source_id' läuft nun von 1 bis {len(merged_data)}.")
    print(f"Die Datei wurde als '{output_file}' gespeichert.")

# Deine Dateiliste
dateien = [
    "/home/s3pr/UNI/BT/code/data/dataset/empirical_research/merged.json",
    "/home/s3pr/UNI/BT/code/data/dataset/nlp4re/merged.json"
]

# Ausführung des Programms
if __name__ == "__main__":
    merge_json_files(dateien, "merged_output.json")