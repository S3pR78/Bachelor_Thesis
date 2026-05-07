# Dataset Analysis Report

Generated at UTC: `2026-05-07T12:30:48.494206+00:00`

## 1. Zweck dieses Reports

Dieser Report analysiert den konsolidierten Master-Datensatz sowie die finalen experimentellen Direct-SPARQL- und PGMR-lite-Dateien. Die Master-Datei wird für globale Dataset-Statistiken verwendet. Die finalen JSON-Dateien werden separat ausgeparamet, weil ACE-Dateien und Paraphrasen-Dateien nicht einfach additiv als disjunkte Splits gezählt werden dürfen.

## 2. Master Dataset

Path: `code/data/dataset/working/master_validated_with_paraphrases_split_v2_no_prefixes.json`

- Items: **762**
- Unique IDs: **762**
- Duplicate ID count: **0**

### 2.1 Paraphrases

- Entries with paraphrased questions: **762**
- Entries without paraphrased questions: **0**
- Total paraphrase strings: **762**

### 2.2 Master Distributions

#### `split`

| param | count |
|---|---:|
| `train` | 602 |
| `test` | 80 |
| `validation` | 80 |

#### `family`

| param | count |
|---|---:|
| `empirical_research_practice` | 403 |
| `nlp4re` | 359 |

#### `source_dataset`

| param | count |
|---|---:|
| `Generated_Empirical_Research` | 330 |
| `Generated_NLP4RE` | 310 |
| `Hybrid_Empirical_Research` | 61 |
| `Hybrid_NLP4RE` | 39 |
| `EmpiRE_Compass` | 22 |

#### `answer_type`

| param | count |
|---|---:|
| `resource` | 202 |
| `string` | 176 |
| `number` | 144 |
| `date` | 118 |
| `mixed` | 78 |
| `list` | 34 |
| `boolean` | 10 |

#### `query_type`

| param | count |
|---|---:|
| `factoid` | 543 |
| `non_factoid` | 219 |

#### `query_shape`

| param | count |
|---|---:|
| `edge` | 350 |
| `tree` | 297 |
| `chain` | 63 |
| `star` | 45 |
| `forest` | 7 |

#### `complexity_level`

| param | count |
|---|---:|
| `low` | 468 |
| `medium` | 195 |
| `high` | 99 |

#### `human_or_generated`

| param | count |
|---|---:|
| `generated` | 641 |
| `hybrid` | 100 |
| `human` | 21 |

#### `review_status`

| param | count |
|---|---:|
| `reviewed` | 640 |
| `approved` | 122 |

#### `gold_status`

| param | count |
|---|---:|
| `validated` | 640 |
| `final` | 122 |

#### `number_of_patterns`

| param | count |
|---|---:|
| `1` | 347 |
| `7` | 81 |
| `6` | 80 |
| `8` | 68 |
| `5` | 50 |
| `9` | 36 |
| `4` | 18 |
| `10` | 17 |
| `11` | 17 |
| `13` | 8 |
| `15` | 7 |
| `17` | 6 |
| `12` | 6 |
| `3` | 6 |
| `25` | 2 |
| `19` | 2 |
| `22` | 2 |
| `31` | 1 |
| `57` | 1 |
| `27` | 1 |
| `30` | 1 |
| `16` | 1 |
| `2` | 1 |
| `24` | 1 |
| `21` | 1 |
| `18` | 1 |

#### `special_types`

- Entries with non-empty list: **497**
- Entries with empty list: **265**
- Entries missing field: **0**

| param | count |
|---|---:|
| `multi_hop` | 311 |
| `lookup` | 244 |
| `string_operation` | 170 |
| `typed_lookup` | 95 |
| `aggregation` | 89 |
| `temporal` | 76 |
| `ranking` | 67 |
| `count` | 62 |
| `comparison` | 58 |
| `superlative` | 48 |
| `multi_intent` | 39 |
| `negation` | 38 |
| `missing_info` | 28 |
| `boolean` | 11 |
| `<empty_list>` | 265 |

#### `query_components`

- Entries with non-empty list: **415**
- Entries with empty list: **347**
- Entries missing field: **0**

| param | count |
|---|---:|
| `SELECT` | 406 |
| `FILTER` | 248 |
| `ORDER_BY` | 217 |
| `OPTIONAL` | 198 |
| `STR` | 169 |
| `COUNT` | 74 |
| `GROUP_BY` | 68 |
| `REGEX` | 44 |
| `NOT_EXISTS` | 33 |
| `MAX` | 16 |
| `MIN` | 15 |
| `BIND` | 14 |
| `LIMIT` | 14 |
| `UNION` | 13 |
| `ASK` | 11 |
| `HAVING` | 9 |
| `AVG` | 6 |
| `IF` | 1 |
| `<empty_list>` | 347 |


## 3. Direct-SPARQL Final Files

| Datei | Items | Unique IDs | Duplicate IDs | With paraphrases | Total paraphrase strings |
|---|---:|---:|---:|---:|---:|
| `train.json` | 602 | 602 | 0 | 602 | 602 |
| `train_with_paraphrases.json` | 1204 | 1204 | 0 | 0 | 0 |
| `validation.json` | 50 | 50 | 0 | 50 | 50 |
| `benchmark.json` | 51 | 51 | 0 | 51 | 51 |
| `ace_playbook.json` | 59 | 59 | 0 | 59 | 59 |
| `ace_dev_pool.json` | 711 | 711 | 0 | 711 | 711 |

### 3.1 Direct-SPARQL Overlaps

| Dateien | Overlap | Beispiel-IDs, erste 50 |
|---|---:|---|
| `train.json ∩ train_with_paraphrases.json` | 602 | `1, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 111, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 127, 129, 130, 131, 132, 133, 135, 136, 137, 140, 141, 142, 144, 145, 146, 147, 148, 149, 150, 151, 152, 154, 155, 156, 157` |
| `train.json ∩ ace_dev_pool.json` | 602 | `1, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 111, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 127, 129, 130, 131, 132, 133, 135, 136, 137, 140, 141, 142, 144, 145, 146, 147, 148, 149, 150, 151, 152, 154, 155, 156, 157` |
| `train_with_paraphrases.json ∩ ace_dev_pool.json` | 602 | `1, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 111, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 127, 129, 130, 131, 132, 133, 135, 136, 137, 140, 141, 142, 144, 145, 146, 147, 148, 149, 150, 151, 152, 154, 155, 156, 157` |
| `validation.json ∩ ace_dev_pool.json` | 50 | `128, 134, 139, 143, 153, 160, 168, 169, 177, 191, 202, 205, 216, 279, 280, 291, 300, 320, 327, 365, 378, 382, 40, 411, 429, 436, 454, 465, 479, 493, 50, 510, 515, 522, 534, 55, 550, 560, 578, 583, 613, 625, 628, 636, 676, 746, 748, 788, 85, 95` |
| `ace_playbook.json ∩ ace_dev_pool.json` | 59 | `106, 112, 126, 138, 194, 203, 219, 271, 281, 312, 336, 346, 356, 370, 374, 383, 385, 399, 402, 441, 45, 463, 495, 500, 51, 519, 530, 535, 540, 558, 588, 629, 632, 657, 67, 678, 711, 712, 713, 714, 715, 750, 751, 764, 765, 775, 795, 799, 801, 802` |

### 3.2 Direct-SPARQL Per-File Distributions

### `train.json`

Path: `code/data/dataset/final/train.json`

- Items: **602**
- Unique IDs: **602**
- Duplicate ID count: **0**

#### Paraphrases

- Entries with paraphrased questions: **602**
- Entries without paraphrased questions: **0**
- Total paraphrase strings: **602**

#### `split`

| param | count |
|---|---:|
| `train` | 602 |

#### `family`

| param | count |
|---|---:|
| `empirical_research_practice` | 325 |
| `nlp4re` | 277 |

#### `source_dataset`

| param | count |
|---|---:|
| `Generated_Empirical_Research` | 287 |
| `Generated_NLP4RE` | 269 |
| `Hybrid_Empirical_Research` | 38 |
| `Hybrid_NLP4RE` | 8 |

#### `answer_type`

| param | count |
|---|---:|
| `resource` | 174 |
| `string` | 153 |
| `number` | 127 |
| `date` | 102 |
| `mixed` | 34 |
| `list` | 9 |
| `boolean` | 3 |

#### `query_type`

| param | count |
|---|---:|
| `factoid` | 424 |
| `non_factoid` | 178 |

#### `query_shape`

| param | count |
|---|---:|
| `edge` | 303 |
| `tree` | 202 |
| `chain` | 52 |
| `star` | 40 |
| `forest` | 5 |

#### `complexity_level`

| param | count |
|---|---:|
| `low` | 391 |
| `medium` | 146 |
| `high` | 65 |

#### `human_or_generated`

| param | count |
|---|---:|
| `generated` | 556 |
| `hybrid` | 46 |

#### `review_status`

| param | count |
|---|---:|
| `reviewed` | 556 |
| `approved` | 46 |

#### `gold_status`

| param | count |
|---|---:|
| `validated` | 556 |
| `final` | 46 |

#### `number_of_patterns`

| param | count |
|---|---:|
| `1` | 300 |
| `7` | 65 |
| `6` | 64 |
| `8` | 47 |
| `5` | 41 |
| `9` | 22 |
| `4` | 15 |
| `11` | 8 |
| `10` | 8 |
| `15` | 6 |
| `3` | 6 |
| `12` | 4 |
| `13` | 3 |
| `17` | 3 |
| `22` | 2 |
| `30` | 1 |
| `16` | 1 |
| `2` | 1 |
| `24` | 1 |
| `25` | 1 |
| `21` | 1 |
| `18` | 1 |
| `19` | 1 |

#### `special_types`

- Entries with non-empty list: **372**
- Entries with empty list: **230**
- Entries missing field: **0**

| param | count |
|---|---:|
| `multi_hop` | 209 |
| `lookup` | 169 |
| `string_operation` | 130 |
| `ranking` | 56 |
| `aggregation` | 55 |
| `temporal` | 55 |
| `typed_lookup` | 54 |
| `count` | 52 |
| `comparison` | 40 |
| `superlative` | 34 |
| `negation` | 25 |
| `multi_intent` | 21 |
| `missing_info` | 15 |
| `boolean` | 4 |
| `<empty_list>` | 230 |

#### `query_components`

- Entries with non-empty list: **302**
- Entries with empty list: **300**
- Entries missing field: **0**

| param | count |
|---|---:|
| `SELECT` | 299 |
| `FILTER` | 179 |
| `ORDER_BY` | 146 |
| `STR` | 130 |
| `OPTIONAL` | 126 |
| `COUNT` | 58 |
| `GROUP_BY` | 38 |
| `REGEX` | 38 |
| `NOT_EXISTS` | 23 |
| `MAX` | 13 |
| `LIMIT` | 13 |
| `UNION` | 12 |
| `BIND` | 11 |
| `MIN` | 11 |
| `AVG` | 6 |
| `HAVING` | 6 |
| `ASK` | 4 |
| `<empty_list>` | 300 |

### `train_with_paraphrases.json`

Path: `code/data/dataset/final/train_with_paraphrases.json`

- Items: **1204**
- Unique IDs: **1204**
- Duplicate ID count: **0**

#### Paraphrases

- Entries with paraphrased questions: **0**
- Entries without paraphrased questions: **1204**
- Total paraphrase strings: **0**

#### `split`

| param | count |
|---|---:|
| `train` | 1204 |

#### `family`

| param | count |
|---|---:|
| `empirical_research_practice` | 650 |
| `nlp4re` | 554 |

#### `source_dataset`

| param | count |
|---|---:|
| `Generated_Empirical_Research` | 574 |
| `Generated_NLP4RE` | 538 |
| `Hybrid_Empirical_Research` | 76 |
| `Hybrid_NLP4RE` | 16 |

#### `answer_type`

| param | count |
|---|---:|
| `resource` | 348 |
| `string` | 306 |
| `number` | 254 |
| `date` | 204 |
| `mixed` | 68 |
| `list` | 18 |
| `boolean` | 6 |

#### `query_type`

| param | count |
|---|---:|
| `factoid` | 848 |
| `non_factoid` | 356 |

#### `query_shape`

| param | count |
|---|---:|
| `edge` | 606 |
| `tree` | 404 |
| `chain` | 104 |
| `star` | 80 |
| `forest` | 10 |

#### `complexity_level`

| param | count |
|---|---:|
| `low` | 782 |
| `medium` | 292 |
| `high` | 130 |

#### `human_or_generated`

| param | count |
|---|---:|
| `generated` | 1112 |
| `hybrid` | 92 |

#### `review_status`

| param | count |
|---|---:|
| `reviewed` | 1112 |
| `approved` | 92 |

#### `gold_status`

| param | count |
|---|---:|
| `validated` | 1112 |
| `final` | 92 |

#### `number_of_patterns`

| param | count |
|---|---:|
| `1` | 600 |
| `7` | 130 |
| `6` | 128 |
| `8` | 94 |
| `5` | 82 |
| `9` | 44 |
| `4` | 30 |
| `11` | 16 |
| `10` | 16 |
| `15` | 12 |
| `3` | 12 |
| `12` | 8 |
| `13` | 6 |
| `17` | 6 |
| `22` | 4 |
| `25` | 2 |
| `24` | 2 |
| `2` | 2 |
| `18` | 2 |
| `30` | 2 |
| `21` | 2 |
| `19` | 2 |
| `16` | 2 |

#### `special_types`

- Entries with non-empty list: **744**
- Entries with empty list: **460**
- Entries missing field: **0**

| param | count |
|---|---:|
| `multi_hop` | 418 |
| `lookup` | 338 |
| `string_operation` | 260 |
| `ranking` | 112 |
| `aggregation` | 110 |
| `temporal` | 110 |
| `typed_lookup` | 108 |
| `count` | 104 |
| `comparison` | 80 |
| `superlative` | 68 |
| `negation` | 50 |
| `multi_intent` | 42 |
| `missing_info` | 30 |
| `boolean` | 8 |
| `<empty_list>` | 460 |

#### `query_components`

- Entries with non-empty list: **604**
- Entries with empty list: **600**
- Entries missing field: **0**

| param | count |
|---|---:|
| `SELECT` | 598 |
| `FILTER` | 358 |
| `ORDER_BY` | 292 |
| `STR` | 260 |
| `OPTIONAL` | 252 |
| `COUNT` | 116 |
| `REGEX` | 76 |
| `GROUP_BY` | 76 |
| `NOT_EXISTS` | 46 |
| `LIMIT` | 26 |
| `MAX` | 26 |
| `UNION` | 24 |
| `MIN` | 22 |
| `BIND` | 22 |
| `AVG` | 12 |
| `HAVING` | 12 |
| `ASK` | 8 |
| `<empty_list>` | 600 |

### `validation.json`

Path: `code/data/dataset/final/validation.json`

- Items: **50**
- Unique IDs: **50**
- Duplicate ID count: **0**

#### Paraphrases

- Entries with paraphrased questions: **50**
- Entries without paraphrased questions: **0**
- Total paraphrase strings: **50**

#### `split`

| param | count |
|---|---:|
| `validation` | 50 |

#### `family`

| param | count |
|---|---:|
| `empirical_research_practice` | 26 |
| `nlp4re` | 24 |

#### `source_dataset`

| param | count |
|---|---:|
| `Generated_Empirical_Research` | 24 |
| `Generated_NLP4RE` | 23 |
| `Hybrid_Empirical_Research` | 2 |
| `Hybrid_NLP4RE` | 1 |

#### `answer_type`

| param | count |
|---|---:|
| `resource` | 15 |
| `string` | 14 |
| `date` | 9 |
| `number` | 9 |
| `mixed` | 3 |

#### `query_type`

| param | count |
|---|---:|
| `factoid` | 36 |
| `non_factoid` | 14 |

#### `query_shape`

| param | count |
|---|---:|
| `edge` | 26 |
| `tree` | 17 |
| `chain` | 4 |
| `star` | 3 |

#### `complexity_level`

| param | count |
|---|---:|
| `low` | 33 |
| `medium` | 12 |
| `high` | 5 |

#### `human_or_generated`

| param | count |
|---|---:|
| `generated` | 47 |
| `hybrid` | 3 |

#### `review_status`

| param | count |
|---|---:|
| `reviewed` | 47 |
| `approved` | 3 |

#### `gold_status`

| param | count |
|---|---:|
| `validated` | 47 |
| `final` | 3 |

#### `number_of_patterns`

| param | count |
|---|---:|
| `1` | 26 |
| `5` | 5 |
| `8` | 5 |
| `9` | 4 |
| `7` | 4 |
| `6` | 3 |
| `13` | 1 |
| `4` | 1 |
| `19` | 1 |

#### `special_types`

- Entries with non-empty list: **31**
- Entries with empty list: **19**
- Entries missing field: **0**

| param | count |
|---|---:|
| `multi_hop` | 19 |
| `string_operation` | 12 |
| `lookup` | 12 |
| `aggregation` | 7 |
| `temporal` | 6 |
| `superlative` | 5 |
| `ranking` | 5 |
| `typed_lookup` | 5 |
| `negation` | 2 |
| `missing_info` | 2 |
| `count` | 2 |
| `comparison` | 2 |
| `multi_intent` | 1 |
| `<empty_list>` | 19 |

#### `query_components`

- Entries with non-empty list: **24**
- Entries with empty list: **26**
- Entries missing field: **0**

| param | count |
|---|---:|
| `SELECT` | 24 |
| `FILTER` | 14 |
| `ORDER_BY` | 12 |
| `STR` | 12 |
| `OPTIONAL` | 10 |
| `REGEX` | 4 |
| `GROUP_BY` | 4 |
| `MIN` | 3 |
| `COUNT` | 3 |
| `NOT_EXISTS` | 2 |
| `LIMIT` | 1 |
| `BIND` | 1 |
| `MAX` | 1 |
| `<empty_list>` | 26 |

### `benchmark.json`

Path: `code/data/dataset/final/benchmark.json`

- Items: **51**
- Unique IDs: **51**
- Duplicate ID count: **0**

#### Paraphrases

- Entries with paraphrased questions: **51**
- Entries without paraphrased questions: **0**
- Total paraphrase strings: **51**

#### `split`

| param | count |
|---|---:|
| `benchmark` | 51 |

#### `family`

| param | count |
|---|---:|
| `nlp4re` | 27 |
| `empirical_research_practice` | 24 |

#### `source_dataset`

| param | count |
|---|---:|
| `Hybrid_NLP4RE` | 25 |
| `Hybrid_Empirical_Research` | 14 |
| `EmpiRE_Compass` | 12 |

#### `answer_type`

| param | count |
|---|---:|
| `mixed` | 35 |
| `list` | 13 |
| `boolean` | 3 |

#### `query_type`

| param | count |
|---|---:|
| `factoid` | 37 |
| `non_factoid` | 14 |

#### `query_shape`

| param | count |
|---|---:|
| `tree` | 49 |
| `forest` | 2 |

#### `complexity_level`

| param | count |
|---|---:|
| `medium` | 24 |
| `high` | 20 |
| `low` | 7 |

#### `human_or_generated`

| param | count |
|---|---:|
| `hybrid` | 39 |
| `human` | 11 |
| `generated` | 1 |

#### `review_status`

| param | count |
|---|---:|
| `approved` | 51 |

#### `gold_status`

| param | count |
|---|---:|
| `final` | 51 |

#### `number_of_patterns`

| param | count |
|---|---:|
| `10` | 8 |
| `6` | 8 |
| `9` | 7 |
| `8` | 7 |
| `11` | 6 |
| `7` | 3 |
| `17` | 2 |
| `13` | 2 |
| `5` | 2 |
| `31` | 1 |
| `57` | 1 |
| `12` | 1 |
| `25` | 1 |
| `27` | 1 |
| `4` | 1 |

#### `special_types`

- Entries with non-empty list: **51**
- Entries with empty list: **0**
- Entries missing field: **0**

| param | count |
|---|---:|
| `multi_hop` | 50 |
| `lookup` | 37 |
| `typed_lookup` | 25 |
| `aggregation` | 23 |
| `string_operation` | 16 |
| `multi_intent` | 15 |
| `temporal` | 11 |
| `comparison` | 10 |
| `missing_info` | 6 |
| `negation` | 5 |
| `superlative` | 5 |
| `count` | 4 |
| `boolean` | 3 |
| `ranking` | 2 |

#### `query_components`

- Entries with non-empty list: **51**
- Entries with empty list: **0**
- Entries missing field: **0**

| param | count |
|---|---:|
| `SELECT` | 49 |
| `OPTIONAL` | 40 |
| `ORDER_BY` | 36 |
| `FILTER` | 34 |
| `GROUP_BY` | 23 |
| `STR` | 15 |
| `COUNT` | 9 |
| `NOT_EXISTS` | 4 |
| `HAVING` | 3 |
| `ASK` | 3 |
| `MAX` | 2 |
| `BIND` | 1 |
| `IF` | 1 |

### `ace_playbook.json`

Path: `code/data/dataset/final/ace_playbook.json`

- Items: **59**
- Unique IDs: **59**
- Duplicate ID count: **0**

#### Paraphrases

- Entries with paraphrased questions: **59**
- Entries without paraphrased questions: **0**
- Total paraphrase strings: **59**

#### `split`

| param | count |
|---|---:|
| `ace_playbook` | 59 |

#### `family`

| param | count |
|---|---:|
| `nlp4re` | 31 |
| `empirical_research_practice` | 28 |

#### `source_dataset`

| param | count |
|---|---:|
| `Generated_Empirical_Research` | 19 |
| `Generated_NLP4RE` | 18 |
| `EmpiRE_Compass` | 10 |
| `Hybrid_Empirical_Research` | 7 |
| `Hybrid_NLP4RE` | 5 |

#### `answer_type`

| param | count |
|---|---:|
| `resource` | 13 |
| `list` | 12 |
| `string` | 9 |
| `number` | 8 |
| `date` | 7 |
| `mixed` | 6 |
| `boolean` | 4 |

#### `query_type`

| param | count |
|---|---:|
| `factoid` | 46 |
| `non_factoid` | 13 |

#### `query_shape`

| param | count |
|---|---:|
| `tree` | 29 |
| `edge` | 21 |
| `chain` | 7 |
| `star` | 2 |

#### `complexity_level`

| param | count |
|---|---:|
| `low` | 37 |
| `medium` | 13 |
| `high` | 9 |

#### `human_or_generated`

| param | count |
|---|---:|
| `generated` | 37 |
| `hybrid` | 12 |
| `human` | 10 |

#### `review_status`

| param | count |
|---|---:|
| `reviewed` | 37 |
| `approved` | 22 |

#### `gold_status`

| param | count |
|---|---:|
| `validated` | 37 |
| `final` | 22 |

#### `number_of_patterns`

| param | count |
|---|---:|
| `1` | 21 |
| `8` | 9 |
| `7` | 9 |
| `6` | 5 |
| `11` | 3 |
| `9` | 3 |
| `13` | 2 |
| `5` | 2 |
| `15` | 1 |
| `10` | 1 |
| `12` | 1 |
| `17` | 1 |
| `4` | 1 |

#### `special_types`

- Entries with non-empty list: **43**
- Entries with empty list: **16**
- Entries missing field: **0**

| param | count |
|---|---:|
| `multi_hop` | 33 |
| `lookup` | 26 |
| `string_operation` | 12 |
| `typed_lookup` | 11 |
| `comparison` | 6 |
| `negation` | 6 |
| `missing_info` | 5 |
| `temporal` | 4 |
| `superlative` | 4 |
| `ranking` | 4 |
| `count` | 4 |
| `aggregation` | 4 |
| `boolean` | 4 |
| `multi_intent` | 2 |
| `<empty_list>` | 16 |

#### `query_components`

- Entries with non-empty list: **38**
- Entries with empty list: **21**
- Entries missing field: **0**

| param | count |
|---|---:|
| `SELECT` | 34 |
| `ORDER_BY` | 23 |
| `OPTIONAL` | 22 |
| `FILTER` | 21 |
| `STR` | 12 |
| `NOT_EXISTS` | 4 |
| `COUNT` | 4 |
| `ASK` | 4 |
| `GROUP_BY` | 3 |
| `REGEX` | 2 |
| `MIN` | 1 |
| `UNION` | 1 |
| `BIND` | 1 |
| `<empty_list>` | 21 |

### `ace_dev_pool.json`

Path: `code/data/dataset/final/ace_dev_pool.json`

- Items: **711**
- Unique IDs: **711**
- Duplicate ID count: **0**

#### Paraphrases

- Entries with paraphrased questions: **711**
- Entries without paraphrased questions: **0**
- Total paraphrase strings: **711**

#### `split`

| param | count |
|---|---:|
| `ace_dev_pool` | 711 |

#### `family`

| param | count |
|---|---:|
| `empirical_research_practice` | 379 |
| `nlp4re` | 332 |

#### `source_dataset`

| param | count |
|---|---:|
| `Generated_Empirical_Research` | 330 |
| `Generated_NLP4RE` | 310 |
| `Hybrid_Empirical_Research` | 47 |
| `Hybrid_NLP4RE` | 14 |
| `EmpiRE_Compass` | 10 |

#### `answer_type`

| param | count |
|---|---:|
| `resource` | 202 |
| `string` | 176 |
| `number` | 144 |
| `date` | 118 |
| `mixed` | 43 |
| `list` | 21 |
| `boolean` | 7 |

#### `query_type`

| param | count |
|---|---:|
| `factoid` | 506 |
| `non_factoid` | 205 |

#### `query_shape`

| param | count |
|---|---:|
| `edge` | 350 |
| `tree` | 248 |
| `chain` | 63 |
| `star` | 45 |
| `forest` | 5 |

#### `complexity_level`

| param | count |
|---|---:|
| `low` | 461 |
| `medium` | 171 |
| `high` | 79 |

#### `human_or_generated`

| param | count |
|---|---:|
| `generated` | 640 |
| `hybrid` | 61 |
| `human` | 10 |

#### `review_status`

| param | count |
|---|---:|
| `reviewed` | 640 |
| `approved` | 71 |

#### `gold_status`

| param | count |
|---|---:|
| `validated` | 640 |
| `final` | 71 |

#### `number_of_patterns`

| param | count |
|---|---:|
| `1` | 347 |
| `7` | 78 |
| `6` | 72 |
| `8` | 61 |
| `5` | 48 |
| `9` | 29 |
| `4` | 17 |
| `11` | 11 |
| `10` | 9 |
| `15` | 7 |
| `13` | 6 |
| `3` | 6 |
| `12` | 5 |
| `17` | 4 |
| `19` | 2 |
| `22` | 2 |
| `30` | 1 |
| `16` | 1 |
| `2` | 1 |
| `24` | 1 |
| `25` | 1 |
| `21` | 1 |
| `18` | 1 |

#### `special_types`

- Entries with non-empty list: **446**
- Entries with empty list: **265**
- Entries missing field: **0**

| param | count |
|---|---:|
| `multi_hop` | 261 |
| `lookup` | 207 |
| `string_operation` | 154 |
| `typed_lookup` | 70 |
| `aggregation` | 66 |
| `ranking` | 65 |
| `temporal` | 65 |
| `count` | 58 |
| `comparison` | 48 |
| `superlative` | 43 |
| `negation` | 33 |
| `multi_intent` | 24 |
| `missing_info` | 22 |
| `boolean` | 8 |
| `<empty_list>` | 265 |

#### `query_components`

- Entries with non-empty list: **364**
- Entries with empty list: **347**
- Entries missing field: **0**

| param | count |
|---|---:|
| `SELECT` | 357 |
| `FILTER` | 214 |
| `ORDER_BY` | 181 |
| `OPTIONAL` | 158 |
| `STR` | 154 |
| `COUNT` | 65 |
| `GROUP_BY` | 45 |
| `REGEX` | 44 |
| `NOT_EXISTS` | 29 |
| `MIN` | 15 |
| `MAX` | 14 |
| `LIMIT` | 14 |
| `UNION` | 13 |
| `BIND` | 13 |
| `ASK` | 8 |
| `AVG` | 6 |
| `HAVING` | 6 |
| `<empty_list>` | 347 |


## 4. PGMR-lite Final Files

| Datei | Items | Unique IDs | Duplicate IDs | With `gold_pgmr_sparql` | With unmapped terms |
|---|---:|---:|---:|---:|---:|
| `train.json` | 602 | 602 | 0 | 602 | 0 |
| `train_with_paraphrases.json` | 1204 | 1204 | 0 | 1204 | 0 |
| `validation.json` | 50 | 50 | 0 | 50 | 0 |
| `benchmark.json` | 51 | 51 | 0 | 51 | 0 |
| `ace_playbook.json` | 59 | 59 | 0 | 59 | 0 |
| `ace_dev_pool.json` | 711 | 711 | 0 | 711 | 0 |

### 4.1 PGMR-lite Overlaps

| Dateien | Overlap | Beispiel-IDs, erste 50 |
|---|---:|---|
| `train.json ∩ train_with_paraphrases.json` | 602 | `1, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 111, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 127, 129, 130, 131, 132, 133, 135, 136, 137, 140, 141, 142, 144, 145, 146, 147, 148, 149, 150, 151, 152, 154, 155, 156, 157` |
| `train.json ∩ ace_dev_pool.json` | 602 | `1, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 111, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 127, 129, 130, 131, 132, 133, 135, 136, 137, 140, 141, 142, 144, 145, 146, 147, 148, 149, 150, 151, 152, 154, 155, 156, 157` |
| `train_with_paraphrases.json ∩ ace_dev_pool.json` | 602 | `1, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 111, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 127, 129, 130, 131, 132, 133, 135, 136, 137, 140, 141, 142, 144, 145, 146, 147, 148, 149, 150, 151, 152, 154, 155, 156, 157` |
| `validation.json ∩ ace_dev_pool.json` | 50 | `128, 134, 139, 143, 153, 160, 168, 169, 177, 191, 202, 205, 216, 279, 280, 291, 300, 320, 327, 365, 378, 382, 40, 411, 429, 436, 454, 465, 479, 493, 50, 510, 515, 522, 534, 55, 550, 560, 578, 583, 613, 625, 628, 636, 676, 746, 748, 788, 85, 95` |
| `ace_playbook.json ∩ ace_dev_pool.json` | 59 | `106, 112, 126, 138, 194, 203, 219, 271, 281, 312, 336, 346, 356, 370, 374, 383, 385, 399, 402, 441, 45, 463, 495, 500, 51, 519, 530, 535, 540, 558, 588, 629, 632, 657, 67, 678, 711, 712, 713, 714, 715, 764, 765, 775, 776, 795, 799, 801, 802, 808` |

### 4.2 PGMR-lite Per-File Distributions

### `pgmr/train.json`

Path: `code/data/dataset/pgmr/final/train.json`

- Items: **602**
- Unique IDs: **602**
- Duplicate ID count: **0**

#### PGMR Summary

- Entries with `gold_pgmr_sparql`: **602**
- Entries without `gold_pgmr_sparql`: **0**
- Entries with unmapped terms: **0**
- Total unmapped terms: **0**
- Total replaced terms: **4083**

#### `split`

| param | count |
|---|---:|
| `train` | 602 |

#### `family`

| param | count |
|---|---:|
| `empirical_research_practice` | 325 |
| `nlp4re` | 277 |

#### `source_dataset`

| param | count |
|---|---:|
| `Generated_Empirical_Research` | 287 |
| `Generated_NLP4RE` | 269 |
| `Hybrid_Empirical_Research` | 38 |
| `Hybrid_NLP4RE` | 8 |

#### `answer_type`

| param | count |
|---|---:|
| `resource` | 174 |
| `string` | 153 |
| `number` | 127 |
| `date` | 102 |
| `mixed` | 34 |
| `list` | 9 |
| `boolean` | 3 |

#### `query_type`

| param | count |
|---|---:|
| `factoid` | 424 |
| `non_factoid` | 178 |

#### `query_shape`

| param | count |
|---|---:|
| `edge` | 303 |
| `tree` | 202 |
| `chain` | 52 |
| `star` | 40 |
| `forest` | 5 |

#### `complexity_level`

| param | count |
|---|---:|
| `low` | 391 |
| `medium` | 146 |
| `high` | 65 |

#### `human_or_generated`

| param | count |
|---|---:|
| `generated` | 556 |
| `hybrid` | 46 |

#### `review_status`

| param | count |
|---|---:|
| `reviewed` | 556 |
| `approved` | 46 |

#### `gold_status`

| param | count |
|---|---:|
| `validated` | 556 |
| `final` | 46 |

#### `number_of_patterns`

| param | count |
|---|---:|
| `1` | 300 |
| `7` | 65 |
| `6` | 64 |
| `8` | 47 |
| `5` | 41 |
| `9` | 22 |
| `4` | 15 |
| `11` | 8 |
| `10` | 8 |
| `15` | 6 |
| `3` | 6 |
| `12` | 4 |
| `13` | 3 |
| `17` | 3 |
| `22` | 2 |
| `30` | 1 |
| `16` | 1 |
| `2` | 1 |
| `24` | 1 |
| `25` | 1 |
| `21` | 1 |
| `18` | 1 |
| `19` | 1 |

#### `special_types`

- Entries with non-empty list: **372**
- Entries with empty list: **230**
- Entries missing field: **0**

| param | count |
|---|---:|
| `multi_hop` | 209 |
| `lookup` | 169 |
| `string_operation` | 130 |
| `ranking` | 56 |
| `aggregation` | 55 |
| `temporal` | 55 |
| `typed_lookup` | 54 |
| `count` | 52 |
| `comparison` | 40 |
| `superlative` | 34 |
| `negation` | 25 |
| `multi_intent` | 21 |
| `missing_info` | 15 |
| `boolean` | 4 |
| `<empty_list>` | 230 |

#### `query_components`

- Entries with non-empty list: **302**
- Entries with empty list: **300**
- Entries missing field: **0**

| param | count |
|---|---:|
| `SELECT` | 299 |
| `FILTER` | 179 |
| `ORDER_BY` | 146 |
| `STR` | 130 |
| `OPTIONAL` | 126 |
| `COUNT` | 58 |
| `GROUP_BY` | 38 |
| `REGEX` | 38 |
| `NOT_EXISTS` | 23 |
| `MAX` | 13 |
| `LIMIT` | 13 |
| `UNION` | 12 |
| `BIND` | 11 |
| `MIN` | 11 |
| `AVG` | 6 |
| `HAVING` | 6 |
| `ASK` | 4 |
| `<empty_list>` | 300 |

#### `pgmr_status`

| param | count |
|---|---:|
| `ok` | 602 |

#### PGMR Unmapped Term Counts

_Keine parame gefunden._

#### PGMR Replaced Term Counts, Top 50

| param | count |
|---|---:|
| `orkgp:P31` | 602 |
| `orkgc:C27001` | 325 |
| `orkgp:P135046` | 325 |
| `orkgc:C121001` | 277 |
| `orkgp:P15124` | 139 |
| `orkgp:P181011` | 116 |
| `orkgp:P29` | 113 |
| `orkgp:P56008` | 95 |
| `orkgp:P181031` | 77 |
| `orkgp:P1005` | 64 |
| `orkgp:DATA` | 61 |
| `orkgp:P56043` | 61 |
| `orkgp:P7055` | 55 |
| `orkgp:P37330` | 49 |
| `orkgp:P39099` | 48 |
| `orkgp:P181017` | 48 |
| `orkgp:P30001` | 46 |
| `orkgp:P57016` | 46 |
| `orkgp:P181046` | 45 |
| `orkgp:HAS_EVALUATION` | 40 |
| `orkgp:P181032` | 39 |
| `orkgp:P181022` | 37 |
| `orkgp:P1003` | 37 |
| `orkgp:P41703` | 36 |
| `orkgp:P56048` | 35 |
| `orkgp:P2006` | 33 |
| `orkgp:P145012` | 33 |
| `orkgp:P59120` | 31 |
| `orkgp:release` | 30 |
| `orkgp:P181025` | 29 |
| `orkgp:P57039` | 28 |
| `orkgp:P57004` | 27 |
| `orkgp:P181041` | 27 |
| `orkgp:P181020` | 26 |
| `orkgp:P181003` | 25 |
| `orkgp:P55034` | 25 |
| `orkgp:P57038` | 23 |
| `orkgp:P181019` | 23 |
| `orkgp:license` | 23 |
| `orkgp:P35133` | 22 |
| `orkgp:P181036` | 22 |
| `orkgp:P181028` | 22 |
| `orkgp:P57000` | 21 |
| `orkgp:P110006` | 21 |
| `orkgp:P181016` | 21 |
| `orkgp:P181051` | 21 |
| `orkgp:P55039` | 20 |
| `orkgp:P94003` | 20 |
| `orkgp:P2001` | 20 |
| `orkgp:P181027` | 20 |

### `pgmr/train_with_paraphrases.json`

Path: `code/data/dataset/pgmr/final/train_with_paraphrases.json`

- Items: **1204**
- Unique IDs: **1204**
- Duplicate ID count: **0**

#### PGMR Summary

- Entries with `gold_pgmr_sparql`: **1204**
- Entries without `gold_pgmr_sparql`: **0**
- Entries with unmapped terms: **0**
- Total unmapped terms: **0**
- Total replaced terms: **8166**

#### `split`

| param | count |
|---|---:|
| `train` | 1204 |

#### `family`

| param | count |
|---|---:|
| `empirical_research_practice` | 650 |
| `nlp4re` | 554 |

#### `source_dataset`

| param | count |
|---|---:|
| `Generated_Empirical_Research` | 574 |
| `Generated_NLP4RE` | 538 |
| `Hybrid_Empirical_Research` | 76 |
| `Hybrid_NLP4RE` | 16 |

#### `answer_type`

| param | count |
|---|---:|
| `resource` | 348 |
| `string` | 306 |
| `number` | 254 |
| `date` | 204 |
| `mixed` | 68 |
| `list` | 18 |
| `boolean` | 6 |

#### `query_type`

| param | count |
|---|---:|
| `factoid` | 848 |
| `non_factoid` | 356 |

#### `query_shape`

| param | count |
|---|---:|
| `edge` | 606 |
| `tree` | 404 |
| `chain` | 104 |
| `star` | 80 |
| `forest` | 10 |

#### `complexity_level`

| param | count |
|---|---:|
| `low` | 782 |
| `medium` | 292 |
| `high` | 130 |

#### `human_or_generated`

| param | count |
|---|---:|
| `generated` | 1112 |
| `hybrid` | 92 |

#### `review_status`

| param | count |
|---|---:|
| `reviewed` | 1112 |
| `approved` | 92 |

#### `gold_status`

| param | count |
|---|---:|
| `validated` | 1112 |
| `final` | 92 |

#### `number_of_patterns`

| param | count |
|---|---:|
| `1` | 600 |
| `7` | 130 |
| `6` | 128 |
| `8` | 94 |
| `5` | 82 |
| `9` | 44 |
| `4` | 30 |
| `11` | 16 |
| `10` | 16 |
| `15` | 12 |
| `3` | 12 |
| `12` | 8 |
| `13` | 6 |
| `17` | 6 |
| `22` | 4 |
| `25` | 2 |
| `24` | 2 |
| `2` | 2 |
| `18` | 2 |
| `30` | 2 |
| `21` | 2 |
| `19` | 2 |
| `16` | 2 |

#### `special_types`

- Entries with non-empty list: **744**
- Entries with empty list: **460**
- Entries missing field: **0**

| param | count |
|---|---:|
| `multi_hop` | 418 |
| `lookup` | 338 |
| `string_operation` | 260 |
| `ranking` | 112 |
| `aggregation` | 110 |
| `temporal` | 110 |
| `typed_lookup` | 108 |
| `count` | 104 |
| `comparison` | 80 |
| `superlative` | 68 |
| `negation` | 50 |
| `multi_intent` | 42 |
| `missing_info` | 30 |
| `boolean` | 8 |
| `<empty_list>` | 460 |

#### `query_components`

- Entries with non-empty list: **604**
- Entries with empty list: **600**
- Entries missing field: **0**

| param | count |
|---|---:|
| `SELECT` | 598 |
| `FILTER` | 358 |
| `ORDER_BY` | 292 |
| `STR` | 260 |
| `OPTIONAL` | 252 |
| `COUNT` | 116 |
| `REGEX` | 76 |
| `GROUP_BY` | 76 |
| `NOT_EXISTS` | 46 |
| `LIMIT` | 26 |
| `MAX` | 26 |
| `UNION` | 24 |
| `MIN` | 22 |
| `BIND` | 22 |
| `AVG` | 12 |
| `HAVING` | 12 |
| `ASK` | 8 |
| `<empty_list>` | 600 |

#### `pgmr_status`

| param | count |
|---|---:|
| `ok` | 1204 |

#### PGMR Unmapped Term Counts

_Keine parame gefunden._

#### PGMR Replaced Term Counts, Top 50

| param | count |
|---|---:|
| `orkgp:P31` | 1204 |
| `orkgc:C27001` | 650 |
| `orkgp:P135046` | 650 |
| `orkgc:C121001` | 554 |
| `orkgp:P15124` | 278 |
| `orkgp:P181011` | 232 |
| `orkgp:P29` | 226 |
| `orkgp:P56008` | 190 |
| `orkgp:P181031` | 154 |
| `orkgp:P1005` | 128 |
| `orkgp:DATA` | 122 |
| `orkgp:P56043` | 122 |
| `orkgp:P7055` | 110 |
| `orkgp:P37330` | 98 |
| `orkgp:P181017` | 96 |
| `orkgp:P39099` | 96 |
| `orkgp:P57016` | 92 |
| `orkgp:P30001` | 92 |
| `orkgp:P181046` | 90 |
| `orkgp:HAS_EVALUATION` | 80 |
| `orkgp:P181032` | 78 |
| `orkgp:P1003` | 74 |
| `orkgp:P181022` | 74 |
| `orkgp:P41703` | 72 |
| `orkgp:P56048` | 70 |
| `orkgp:P145012` | 66 |
| `orkgp:P2006` | 66 |
| `orkgp:P59120` | 62 |
| `orkgp:release` | 60 |
| `orkgp:P181025` | 58 |
| `orkgp:P57039` | 56 |
| `orkgp:P57004` | 54 |
| `orkgp:P181041` | 54 |
| `orkgp:P181020` | 52 |
| `orkgp:P181003` | 50 |
| `orkgp:P55034` | 50 |
| `orkgp:P181019` | 46 |
| `orkgp:P57038` | 46 |
| `orkgp:license` | 46 |
| `orkgp:P35133` | 44 |
| `orkgp:P181036` | 44 |
| `orkgp:P181028` | 44 |
| `orkgp:P181016` | 42 |
| `orkgp:P110006` | 42 |
| `orkgp:P57000` | 42 |
| `orkgp:P181051` | 42 |
| `orkgp:P55039` | 40 |
| `orkgp:P2001` | 40 |
| `orkgp:P181027` | 40 |
| `orkgp:P94003` | 40 |

### `pgmr/validation.json`

Path: `code/data/dataset/pgmr/final/validation.json`

- Items: **50**
- Unique IDs: **50**
- Duplicate ID count: **0**

#### PGMR Summary

- Entries with `gold_pgmr_sparql`: **50**
- Entries without `gold_pgmr_sparql`: **0**
- Entries with unmapped terms: **0**
- Total unmapped terms: **0**
- Total replaced terms: **354**

#### `split`

| param | count |
|---|---:|
| `validation` | 50 |

#### `family`

| param | count |
|---|---:|
| `empirical_research_practice` | 26 |
| `nlp4re` | 24 |

#### `source_dataset`

| param | count |
|---|---:|
| `Generated_Empirical_Research` | 24 |
| `Generated_NLP4RE` | 23 |
| `Hybrid_Empirical_Research` | 2 |
| `Hybrid_NLP4RE` | 1 |

#### `answer_type`

| param | count |
|---|---:|
| `resource` | 15 |
| `string` | 14 |
| `date` | 9 |
| `number` | 9 |
| `mixed` | 3 |

#### `query_type`

| param | count |
|---|---:|
| `factoid` | 36 |
| `non_factoid` | 14 |

#### `query_shape`

| param | count |
|---|---:|
| `edge` | 26 |
| `tree` | 17 |
| `chain` | 4 |
| `star` | 3 |

#### `complexity_level`

| param | count |
|---|---:|
| `low` | 33 |
| `medium` | 12 |
| `high` | 5 |

#### `human_or_generated`

| param | count |
|---|---:|
| `generated` | 47 |
| `hybrid` | 3 |

#### `review_status`

| param | count |
|---|---:|
| `reviewed` | 47 |
| `approved` | 3 |

#### `gold_status`

| param | count |
|---|---:|
| `validated` | 47 |
| `final` | 3 |

#### `number_of_patterns`

| param | count |
|---|---:|
| `1` | 26 |
| `5` | 5 |
| `8` | 5 |
| `9` | 4 |
| `7` | 4 |
| `6` | 3 |
| `13` | 1 |
| `4` | 1 |
| `19` | 1 |

#### `special_types`

- Entries with non-empty list: **31**
- Entries with empty list: **19**
- Entries missing field: **0**

| param | count |
|---|---:|
| `multi_hop` | 19 |
| `string_operation` | 12 |
| `lookup` | 12 |
| `aggregation` | 7 |
| `temporal` | 6 |
| `superlative` | 5 |
| `ranking` | 5 |
| `typed_lookup` | 5 |
| `negation` | 2 |
| `missing_info` | 2 |
| `count` | 2 |
| `comparison` | 2 |
| `multi_intent` | 1 |
| `<empty_list>` | 19 |

#### `query_components`

- Entries with non-empty list: **24**
- Entries with empty list: **26**
- Entries missing field: **0**

| param | count |
|---|---:|
| `SELECT` | 24 |
| `FILTER` | 14 |
| `ORDER_BY` | 12 |
| `STR` | 12 |
| `OPTIONAL` | 10 |
| `REGEX` | 4 |
| `GROUP_BY` | 4 |
| `MIN` | 3 |
| `COUNT` | 3 |
| `NOT_EXISTS` | 2 |
| `LIMIT` | 1 |
| `BIND` | 1 |
| `MAX` | 1 |
| `<empty_list>` | 26 |

#### `pgmr_status`

| param | count |
|---|---:|
| `ok` | 50 |

#### PGMR Unmapped Term Counts

_Keine parame gefunden._

#### PGMR Replaced Term Counts, Top 50

| param | count |
|---|---:|
| `orkgp:P31` | 50 |
| `orkgc:C27001` | 26 |
| `orkgp:P135046` | 26 |
| `orkgc:C121001` | 24 |
| `orkgp:P56008` | 12 |
| `orkgp:P181011` | 12 |
| `orkgp:P15124` | 10 |
| `orkgp:P29` | 10 |
| `orkgp:P1005` | 8 |
| `orkgp:P181046` | 8 |
| `orkgp:DATA` | 6 |
| `orkgp:P145012` | 6 |
| `orkgp:release` | 6 |
| `orkgp:P181017` | 6 |
| `orkgp:P2006` | 5 |
| `orkgp:P57016` | 5 |
| `orkgp:P7055` | 5 |
| `orkgp:P39099` | 4 |
| `orkgp:P57038` | 4 |
| `orkgp:P37330` | 4 |
| `orkgp:P1003` | 4 |
| `orkgp:P181022` | 4 |
| `orkgp:P181018` | 4 |
| `orkgp:P181020` | 4 |
| `orkgp:P56048` | 3 |
| `orkgp:P57039` | 3 |
| `orkgp:P57000` | 3 |
| `orkgp:P2001` | 3 |
| `orkgp:P181003` | 3 |
| `orkgp:P181016` | 3 |
| `orkgp:P181048` | 3 |
| `orkgp:HAS_EVALUATION` | 3 |
| `orkgp:P181031` | 3 |
| `orkgp:P181019` | 3 |
| `orkgp:P41835` | 3 |
| `orkgp:P181025` | 3 |
| `orkgp:P57005` | 2 |
| `orkgp:P57006` | 2 |
| `orkgp:P57010` | 2 |
| `orkgp:P59065` | 2 |
| `orkgp:url` | 2 |
| `orkgp:P59109` | 2 |
| `orkgp:P94003` | 2 |
| `orkgp:P57004` | 2 |
| `orkgp:P56043` | 2 |
| `orkgp:P181004` | 2 |
| `orkgp:P181049` | 2 |
| `orkgp:P110006` | 2 |
| `orkgp:P181032` | 2 |
| `orkgp:P58069` | 2 |

### `pgmr/benchmark.json`

Path: `code/data/dataset/pgmr/final/benchmark.json`

- Items: **51**
- Unique IDs: **51**
- Duplicate ID count: **0**

#### PGMR Summary

- Entries with `gold_pgmr_sparql`: **51**
- Entries without `gold_pgmr_sparql`: **0**
- Entries with unmapped terms: **0**
- Total unmapped terms: **0**
- Total replaced terms: **356**

#### `split`

| param | count |
|---|---:|
| `benchmark` | 49 |
| `ace_playbook` | 2 |

#### `family`

| param | count |
|---|---:|
| `empirical_research_practice` | 26 |
| `nlp4re` | 25 |

#### `source_dataset`

| param | count |
|---|---:|
| `Hybrid_NLP4RE` | 24 |
| `Hybrid_Empirical_Research` | 16 |
| `EmpiRE_Compass` | 11 |

#### `answer_type`

| param | count |
|---|---:|
| `mixed` | 35 |
| `list` | 13 |
| `boolean` | 3 |

#### `query_type`

| param | count |
|---|---:|
| `factoid` | 36 |
| `non_factoid` | 15 |

#### `query_shape`

| param | count |
|---|---:|
| `tree` | 50 |
| `forest` | 1 |

#### `complexity_level`

| param | count |
|---|---:|
| `medium` | 23 |
| `high` | 21 |
| `low` | 7 |

#### `human_or_generated`

| param | count |
|---|---:|
| `hybrid` | 40 |
| `human` | 10 |
| `generated` | 1 |

#### `review_status`

| param | count |
|---|---:|
| `approved` | 51 |

#### `gold_status`

| param | count |
|---|---:|
| `final` | 51 |

#### `number_of_patterns`

| param | count |
|---|---:|
| `10` | 8 |
| `9` | 7 |
| `8` | 7 |
| `6` | 7 |
| `11` | 6 |
| `17` | 3 |
| `13` | 3 |
| `7` | 3 |
| `5` | 2 |
| `31` | 1 |
| `12` | 1 |
| `25` | 1 |
| `27` | 1 |
| `4` | 1 |

#### `special_types`

- Entries with non-empty list: **51**
- Entries with empty list: **0**
- Entries missing field: **0**

| param | count |
|---|---:|
| `multi_hop` | 51 |
| `lookup` | 36 |
| `typed_lookup` | 27 |
| `aggregation` | 23 |
| `multi_intent` | 16 |
| `string_operation` | 16 |
| `temporal` | 12 |
| `comparison` | 11 |
| `superlative` | 7 |
| `count` | 6 |
| `negation` | 5 |
| `missing_info` | 5 |
| `ranking` | 4 |
| `boolean` | 3 |

#### `query_components`

- Entries with non-empty list: **51**
- Entries with empty list: **0**
- Entries missing field: **0**

| param | count |
|---|---:|
| `SELECT` | 49 |
| `OPTIONAL` | 40 |
| `FILTER` | 36 |
| `ORDER_BY` | 36 |
| `GROUP_BY` | 23 |
| `STR` | 14 |
| `COUNT` | 10 |
| `NOT_EXISTS` | 4 |
| `HAVING` | 3 |
| `ASK` | 3 |
| `MAX` | 2 |
| `UNION` | 1 |

#### `pgmr_status`

| param | count |
|---|---:|
| `ok` | 51 |

#### PGMR Unmapped Term Counts

_Keine parame gefunden._

#### PGMR Replaced Term Counts, Top 50

| param | count |
|---|---:|
| `orkgp:P31` | 51 |
| `orkgc:C27001` | 26 |
| `orkgp:P135046` | 25 |
| `orkgc:C121001` | 25 |
| `orkgp:P29` | 16 |
| `orkgp:P56008` | 10 |
| `orkgp:P15124` | 9 |
| `orkgp:P181011` | 8 |
| `orkgp:P37330` | 7 |
| `orkgp:P1005` | 6 |
| `orkgp:P181003` | 6 |
| `orkgp:P56043` | 6 |
| `orkgp:P41928` | 6 |
| `orkgp:P44139` | 5 |
| `orkgp:P94003` | 4 |
| `orkgp:P1003` | 4 |
| `orkgp:P181004` | 4 |
| `orkgp:P35133` | 4 |
| `orkgp:DATA` | 4 |
| `orkgp:P181002` | 4 |
| `orkgp:HAS_EVALUATION` | 4 |
| `orkgp:P181031` | 4 |
| `orkgp:P181016` | 3 |
| `orkgp:P181022` | 3 |
| `orkgp:P181025` | 3 |
| `orkgp:P181028` | 3 |
| `orkgp:P181030` | 3 |
| `orkgp:P7055` | 3 |
| `orkgp:P57000` | 3 |
| `orkgp:P56048` | 3 |
| `orkgp:P181006` | 3 |
| `orkgp:P181007` | 3 |
| `orkgp:P145000` | 2 |
| `orkgp:P39099` | 2 |
| `orkgp:P55034` | 2 |
| `orkgp:P55035` | 2 |
| `orkgp:P55036` | 2 |
| `orkgp:P55037` | 2 |
| `orkgp:P59109` | 2 |
| `orkgp:P60006` | 2 |
| `orkgp:P68005` | 2 |
| `orkgp:P97000` | 2 |
| `orkgp:P97001` | 2 |
| `orkgp:P97002` | 2 |
| `orkgp:P181026` | 2 |
| `orkgp:P181027` | 2 |
| `orkgp:license` | 2 |
| `orkgp:url` | 2 |
| `orkgp:P30001` | 2 |
| `orkgp:P181051` | 2 |

### `pgmr/ace_playbook.json`

Path: `code/data/dataset/pgmr/final/ace_playbook.json`

- Items: **59**
- Unique IDs: **59**
- Duplicate ID count: **0**

#### PGMR Summary

- Entries with `gold_pgmr_sparql`: **59**
- Entries without `gold_pgmr_sparql`: **0**
- Entries with unmapped terms: **0**
- Total unmapped terms: **0**
- Total replaced terms: **431**

#### `split`

| param | count |
|---|---:|
| `ace_playbook` | 57 |
| `benchmark` | 2 |

#### `family`

| param | count |
|---|---:|
| `nlp4re` | 33 |
| `empirical_research_practice` | 26 |

#### `source_dataset`

| param | count |
|---|---:|
| `Generated_Empirical_Research` | 19 |
| `Generated_NLP4RE` | 18 |
| `EmpiRE_Compass` | 11 |
| `Hybrid_NLP4RE` | 6 |
| `Hybrid_Empirical_Research` | 5 |

#### `answer_type`

| param | count |
|---|---:|
| `resource` | 13 |
| `list` | 12 |
| `string` | 9 |
| `number` | 8 |
| `date` | 7 |
| `mixed` | 6 |
| `boolean` | 4 |

#### `query_type`

| param | count |
|---|---:|
| `factoid` | 47 |
| `non_factoid` | 12 |

#### `query_shape`

| param | count |
|---|---:|
| `tree` | 28 |
| `edge` | 21 |
| `chain` | 7 |
| `star` | 2 |
| `forest` | 1 |

#### `complexity_level`

| param | count |
|---|---:|
| `low` | 37 |
| `medium` | 14 |
| `high` | 8 |

#### `human_or_generated`

| param | count |
|---|---:|
| `generated` | 37 |
| `human` | 11 |
| `hybrid` | 11 |

#### `review_status`

| param | count |
|---|---:|
| `reviewed` | 37 |
| `approved` | 22 |

#### `gold_status`

| param | count |
|---|---:|
| `validated` | 37 |
| `final` | 22 |

#### `number_of_patterns`

| param | count |
|---|---:|
| `1` | 21 |
| `8` | 9 |
| `7` | 9 |
| `6` | 6 |
| `11` | 3 |
| `9` | 3 |
| `5` | 2 |
| `15` | 1 |
| `10` | 1 |
| `12` | 1 |
| `13` | 1 |
| `4` | 1 |
| `57` | 1 |

#### `special_types`

- Entries with non-empty list: **43**
- Entries with empty list: **16**
- Entries missing field: **0**

| param | count |
|---|---:|
| `multi_hop` | 32 |
| `lookup` | 27 |
| `string_operation` | 12 |
| `typed_lookup` | 9 |
| `negation` | 6 |
| `missing_info` | 6 |
| `comparison` | 5 |
| `aggregation` | 4 |
| `boolean` | 4 |
| `temporal` | 3 |
| `superlative` | 2 |
| `ranking` | 2 |
| `count` | 2 |
| `multi_intent` | 1 |
| `<empty_list>` | 16 |

#### `query_components`

- Entries with non-empty list: **38**
- Entries with empty list: **21**
- Entries missing field: **0**

| param | count |
|---|---:|
| `SELECT` | 34 |
| `ORDER_BY` | 23 |
| `OPTIONAL` | 22 |
| `FILTER` | 19 |
| `STR` | 13 |
| `NOT_EXISTS` | 4 |
| `ASK` | 4 |
| `COUNT` | 3 |
| `GROUP_BY` | 3 |
| `REGEX` | 2 |
| `BIND` | 2 |
| `MIN` | 1 |
| `IF` | 1 |
| `<empty_list>` | 21 |

#### `pgmr_status`

| param | count |
|---|---:|
| `ok` | 59 |

#### PGMR Unmapped Term Counts

_Keine parame gefunden._

#### PGMR Replaced Term Counts, Top 50

| param | count |
|---|---:|
| `orkgp:P31` | 59 |
| `orkgc:C121001` | 33 |
| `orkgc:C27001` | 26 |
| `orkgp:P135046` | 26 |
| `orkgp:P181011` | 14 |
| `orkgp:P15124` | 13 |
| `orkgp:P29` | 10 |
| `orkgp:P181031` | 8 |
| `orkgp:P181046` | 7 |
| `orkgp:P56008` | 6 |
| `orkgp:P181003` | 6 |
| `orkgp:HAS_EVALUATION` | 6 |
| `orkgp:P1005` | 5 |
| `orkgp:P181032` | 5 |
| `orkgp:P59120` | 5 |
| `orkgp:P181022` | 5 |
| `orkgp:P56043` | 5 |
| `orkgp:P1003` | 5 |
| `orkgp:P110006` | 4 |
| `orkgp:P56048` | 4 |
| `orkgp:P2006` | 4 |
| `orkgp:P3004` | 4 |
| `orkgp:P57016` | 4 |
| `orkgp:license` | 4 |
| `orkgp:P181025` | 4 |
| `orkgp:release` | 4 |
| `orkgp:P181028` | 4 |
| `orkgp:P145012` | 3 |
| `orkgp:P94003` | 3 |
| `orkgp:P181036` | 3 |
| `orkgp:P181038` | 3 |
| `orkgp:P181004` | 3 |
| `orkgp:P181051` | 3 |
| `orkgp:P181052` | 3 |
| `orkgp:P37330` | 3 |
| `orkgp:DATA` | 3 |
| `orkgp:P7055` | 3 |
| `orkgp:P30001` | 3 |
| `orkgp:P41703` | 3 |
| `orkgp:P181017` | 3 |
| `orkgp:P181020` | 3 |
| `orkgp:P181048` | 3 |
| `orkgp:P57005` | 3 |
| `orkgp:P39099` | 3 |
| `orkgp:P35133` | 3 |
| `orkgp:P5073` | 3 |
| `orkgp:P181016` | 3 |
| `orkgp:P181026` | 3 |
| `orkgp:P181006` | 3 |
| `orkgp:P181009` | 3 |

### `pgmr/ace_dev_pool.json`

Path: `code/data/dataset/pgmr/final/ace_dev_pool.json`

- Items: **711**
- Unique IDs: **711**
- Duplicate ID count: **0**

#### PGMR Summary

- Entries with `gold_pgmr_sparql`: **711**
- Entries without `gold_pgmr_sparql`: **0**
- Entries with unmapped terms: **0**
- Total unmapped terms: **0**
- Total replaced terms: **4868**

#### `split`

| param | count |
|---|---:|
| `ace_dev_pool` | 711 |

#### `family`

| param | count |
|---|---:|
| `empirical_research_practice` | 377 |
| `nlp4re` | 334 |

#### `source_dataset`

| param | count |
|---|---:|
| `Generated_Empirical_Research` | 330 |
| `Generated_NLP4RE` | 310 |
| `Hybrid_Empirical_Research` | 45 |
| `Hybrid_NLP4RE` | 15 |
| `EmpiRE_Compass` | 11 |

#### `answer_type`

| param | count |
|---|---:|
| `resource` | 202 |
| `string` | 176 |
| `number` | 144 |
| `date` | 118 |
| `mixed` | 43 |
| `list` | 21 |
| `boolean` | 7 |

#### `query_type`

| param | count |
|---|---:|
| `factoid` | 507 |
| `non_factoid` | 204 |

#### `query_shape`

| param | count |
|---|---:|
| `edge` | 350 |
| `tree` | 247 |
| `chain` | 63 |
| `star` | 45 |
| `forest` | 6 |

#### `complexity_level`

| param | count |
|---|---:|
| `low` | 461 |
| `medium` | 172 |
| `high` | 78 |

#### `human_or_generated`

| param | count |
|---|---:|
| `generated` | 640 |
| `hybrid` | 60 |
| `human` | 11 |

#### `review_status`

| param | count |
|---|---:|
| `reviewed` | 640 |
| `approved` | 71 |

#### `gold_status`

| param | count |
|---|---:|
| `validated` | 640 |
| `final` | 71 |

#### `number_of_patterns`

| param | count |
|---|---:|
| `1` | 347 |
| `7` | 78 |
| `6` | 73 |
| `8` | 61 |
| `5` | 48 |
| `9` | 29 |
| `4` | 17 |
| `11` | 11 |
| `10` | 9 |
| `15` | 7 |
| `3` | 6 |
| `12` | 5 |
| `13` | 5 |
| `17` | 3 |
| `19` | 2 |
| `22` | 2 |
| `30` | 1 |
| `16` | 1 |
| `2` | 1 |
| `24` | 1 |
| `25` | 1 |
| `21` | 1 |
| `18` | 1 |
| `57` | 1 |

#### `special_types`

- Entries with non-empty list: **446**
- Entries with empty list: **265**
- Entries missing field: **0**

| param | count |
|---|---:|
| `multi_hop` | 260 |
| `lookup` | 208 |
| `string_operation` | 154 |
| `typed_lookup` | 68 |
| `aggregation` | 66 |
| `temporal` | 64 |
| `ranking` | 63 |
| `count` | 56 |
| `comparison` | 47 |
| `superlative` | 41 |
| `negation` | 33 |
| `multi_intent` | 23 |
| `missing_info` | 23 |
| `boolean` | 8 |
| `<empty_list>` | 265 |

#### `query_components`

- Entries with non-empty list: **364**
- Entries with empty list: **347**
- Entries missing field: **0**

| param | count |
|---|---:|
| `SELECT` | 357 |
| `FILTER` | 212 |
| `ORDER_BY` | 181 |
| `OPTIONAL` | 158 |
| `STR` | 155 |
| `COUNT` | 64 |
| `GROUP_BY` | 45 |
| `REGEX` | 44 |
| `NOT_EXISTS` | 29 |
| `MIN` | 15 |
| `MAX` | 14 |
| `BIND` | 14 |
| `LIMIT` | 14 |
| `UNION` | 12 |
| `ASK` | 8 |
| `AVG` | 6 |
| `HAVING` | 6 |
| `IF` | 1 |
| `<empty_list>` | 347 |

#### `pgmr_status`

| param | count |
|---|---:|
| `ok` | 711 |

#### PGMR Unmapped Term Counts

_Keine parame gefunden._

#### PGMR Replaced Term Counts, Top 50

| param | count |
|---|---:|
| `orkgp:P31` | 711 |
| `orkgc:C27001` | 377 |
| `orkgp:P135046` | 377 |
| `orkgc:C121001` | 334 |
| `orkgp:P15124` | 162 |
| `orkgp:P181011` | 142 |
| `orkgp:P29` | 133 |
| `orkgp:P56008` | 113 |
| `orkgp:P181031` | 88 |
| `orkgp:P1005` | 77 |
| `orkgp:DATA` | 70 |
| `orkgp:P56043` | 68 |
| `orkgp:P7055` | 63 |
| `orkgp:P181046` | 60 |
| `orkgp:P181017` | 57 |
| `orkgp:P37330` | 56 |
| `orkgp:P57016` | 55 |
| `orkgp:P39099` | 55 |
| `orkgp:P30001` | 50 |
| `orkgp:HAS_EVALUATION` | 49 |
| `orkgp:P181022` | 46 |
| `orkgp:P181032` | 46 |
| `orkgp:P1003` | 46 |
| `orkgp:P2006` | 42 |
| `orkgp:P56048` | 42 |
| `orkgp:P145012` | 42 |
| `orkgp:release` | 40 |
| `orkgp:P41703` | 40 |
| `orkgp:P59120` | 37 |
| `orkgp:P181025` | 36 |
| `orkgp:P181003` | 34 |
| `orkgp:P181020` | 33 |
| `orkgp:P57039` | 32 |
| `orkgp:P57004` | 31 |
| `orkgp:P181041` | 30 |
| `orkgp:P57038` | 29 |
| `orkgp:P181028` | 28 |
| `orkgp:license` | 28 |
| `orkgp:P110006` | 27 |
| `orkgp:P181019` | 27 |
| `orkgp:P181016` | 27 |
| `orkgp:P55034` | 27 |
| `orkgp:P57000` | 26 |
| `orkgp:P35133` | 26 |
| `orkgp:P94003` | 25 |
| `orkgp:P181036` | 25 |
| `orkgp:P181051` | 25 |
| `orkgp:P2001` | 24 |
| `orkgp:P181027` | 24 |
| `orkgp:P55039` | 22 |


## 5. Interpretation Notes

- The master file should be used for global statements about the dataset, e.g., total size, family distribution, sources, answer types, and complexity distribution.
- The final Direct-SPARQL files should be described for the actual experimental use.
- `train_with_paraphrases.json` is a training variant with additional linguistic variants and should not be counted as an additional amount of original questions.
- `ace_dev_pool.json` is an ACE development pool and may overlap with other files. The overlap table shows which files contain common IDs.
- The PGMR-lite files reflect the experimental files with additional placeholder-based target representation.
