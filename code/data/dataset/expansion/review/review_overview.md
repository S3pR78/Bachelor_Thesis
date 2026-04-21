# Dataset Expansion Review Overview

## Purpose

This file tracks the current review status of generated candidate batches for dataset expansion.

It is intended to help decide:
- which batches are already usable as candidate pools
- which batches need schema review
- which batches contain suspicious predicates or logical issues
- whether to generate additional waves now or first consolidate and review

---

## Status legend

- **strong**: batch is broadly usable, with only minor review needed
- **usable**: batch is mostly usable, but has a noticeable number of entries that should be checked
- **review-heavy**: batch contains enough suspicious patterns that a focused review is necessary before relying on it
- **repair-or-regenerate**: batch contains major issues and should be repaired or partially regenerated

---

## Current batch assessment

### B001 — Answer type gaps

#### b001_nlp4re
Status: **strong**

Notes:
- good question–query alignment
- clearly improved after switching to minimal output
- family anchoring is mostly good
- some entries still require schema review if suspicious predicates appear

Action:
- keep as candidate batch
- include in later manual/schema review

### b001_empirical
Status: **strong**

Retain:
- b001_empirical_001
- b001_empirical_002
- b001_empirical_003
- b001_empirical_004
- b001_empirical_005
- b001_empirical_006
- b001_empirical_007
- b001_empirical_008
- b001_empirical_009
- b001_empirical_010

Review/repair:
- none currently required

Notes:
- batch is broadly usable
- no major recurring placeholder pattern stood out in initial review


#### b001_empirical
Status: **strong**

Notes:
- good alignment between question and projection
- empirical family structure looks stable
- answer types are mostly plausible
- generally usable as a candidate pool

Action:
- keep as candidate batch
- include in later manual/schema review

---

Retain:
- 9 entries directly usable as candidate pool

Review/repair:
- 1 entry flagged for suspicious predicate usage

### B002 — Missing query components


### b002_empirical
Status: **usable**

Retain:
- b002_empirical_003
- b002_empirical_004
- b002_empirical_005
- b002_empirical_006
- b002_empirical_009

Review/repair:
- b002_empirical_001
- b002_empirical_002
- b002_empirical_007
- b002_empirical_008
- b002_empirical_010

Notes:
- batch objective is visible and useful
- strongest risks are slightly artificial operator-driven questions and some ranking/query-phrasing mismatches
- batch is usable, but selective retention is better than blind acceptance

### b002_nlp4re
Status: **usable**

Retain:
- b002_nlp4re_004
- b002_nlp4re_005
- b002_nlp4re_006
- b002_nlp4re_009

Review/repair:
- b002_nlp4re_001
- b002_nlp4re_002
- b002_nlp4re_003
- b002_nlp4re_007
- b002_nlp4re_008
- b002_nlp4re_010

Notes:
- batch objective is visible: REGEX, LIMIT, MIN, AVG appear
- strongest issues are suspicious predicates and ranking-query phrasing mismatches
- batch is usable, but selective retention is better than blind acceptance



### B003 — Non-factoid reasoning

#### b003_nlp4re
Status: **usable**

Notes:
- later version is clearly better than the first attempt
- several entries are strong and genuinely reasoning-oriented
- still contains some suspicious predicates such as:
  - `orkgp:HAS_EVALUATION`
  - possibly `orkgp:release`
- some entries should be retained, others flagged for schema review

Action:
- keep as candidate batch
- review suspicious entries individually

Retain:
- b003_nlp4re_004
- b003_nlp4re_005
- b003_nlp4re_006
- b003_nlp4re_008
- b003_nlp4re_009

Review/repair:
- b003_nlp4re_001
- b003_nlp4re_002
- b003_nlp4re_003
- b003_nlp4re_007
- b003_nlp4re_010

Notes:
- later version is clearly better than the first attempt
- several entries are strong and genuinely reasoning-oriented
- repeated suspicious predicates remain the main repair trigger

#### b003_empirical
Status: **strong**

Notes:
- one of the better empirical batches
- good family anchoring
- good use of negation, multi-condition logic, and non-factoid structure
- no major red-flag placeholder pattern stood out

Action:
- keep as candidate batch
- include in later manual/schema review


Retain:
- b003_empirical_001
- b003_empirical_002
- b003_empirical_003
- b003_empirical_004
- b003_empirical_005
- b003_empirical_006
- b003_empirical_007
- b003_empirical_008
- b003_empirical_009
- b003_empirical_010

Review/repair:
- none currently required

Notes:
- one of the better empirical batches
- good family anchoring
- good use of negation, multi-condition logic, and non-factoid structure

---

### B004 — NLP4RE priority

#### b004_nlp4re
Status: **usable**

Notes:
- generally good NLP4RE-specific focus
- several entries are useful and template-relevant
- however, suspicious predicate patterns still appear in some items:
  - `orkgp:HAS_EVALUATION`
  - `orkgp:release`
- some entries feel more like broad template lookup than targeted priority expansion

Action:
- keep as candidate batch
- review suspicious entries individually
- use as supporting NLP4RE expansion material, not as blindly trusted gold candidates


Retain:
- b004_nlp4re_001
- b004_nlp4re_002
- b004_nlp4re_003
- b004_nlp4re_006
- b004_nlp4re_007
- b004_nlp4re_009

Review/repair:
- b004_nlp4re_004
- b004_nlp4re_005
- b004_nlp4re_008
- b004_nlp4re_010

Notes:
- generally good NLP4RE-specific focus
- several entries are useful and template-relevant
- repeated suspicious predicate patterns remain the main review trigger

---

### B005 — Hard case buffer

#### b005_nlp4re
Status: **strong**

Notes:
- one of the better nlp4re batches
- contains harder multi-hop and composite questions
- several entries are well aligned and genuinely useful as hard-case candidates
- still contains a few suspicious predicate cases:
  - `orkgp:HAS_EVALUATION`
  - `orkgp:release`

Action:
- keep as candidate batch
- review suspicious entries individually
- likely strong source for later hard-case selection

Retain:
- b005_nlp4re_002
- b005_nlp4re_003
- b005_nlp4re_005
- b005_nlp4re_006
- b005_nlp4re_007
- b005_nlp4re_008
- b005_nlp4re_010

Review/repair:
- b005_nlp4re_001
- b005_nlp4re_004
- b005_nlp4re_009

Notes:
- one of the better nlp4re batches
- several entries are strong hard-case candidates
- repeated suspicious predicates remain the main repair trigger

#### b005_empirical
Status: **strong**

Notes:
- one of the strongest empirical batches
- good family anchoring
- good hard-case behavior:
  - nested reasoning
  - negation
  - conjunction
  - counting
  - ranking logic
- at least one entry may have query-logic issues and should be inspected separately

Action:
- keep as candidate batch
- review a few complex entries manually
- strong source for later hard-case selection

---

## Common recurring issues

### 1. Suspicious predicate patterns
The most important recurring issue is the appearance of suspicious or placeholder-like predicates, especially in some NLP4RE batches.

Examples:
- `orkgp:HAS_EVALUATION`
- `orkgp:release`

These should be treated as review triggers.

### 2. Complex query logic mismatch
Some hard-case items may look good at the natural-language level but contain a subtle mismatch between:
- the intended reasoning
- the actual SPARQL logic

These should be flagged during review.

### 3. Multi-projection answer type ambiguity
For items that return:
- a paper
- plus one or more additional values

the assigned `answer_type` may be pragmatically acceptable but methodologically slightly underspecified.

This should be acknowledged in the thesis/write-up.

---

## Working recommendation

### Keep and use as current candidate pool
- b001_nlp4re
- b001_empirical
- b003_empirical
- b005_nlp4re
- b005_empirical

### Keep, but review more carefully
- b002_nlp4re
- b002_empirical
- b003_nlp4re
- b004_nlp4re

---

## Current project position

### Generation workflow maturity
Current status: **strong**

Reason:
- prompt assembly works
- minimal-output strategy works
- question–query alignment improved substantially
- family grounding is much better than in earlier attempts

### Candidate dataset maturity
Current status: **mid-stage**

Reason:
- multiple usable candidate batches already exist
- but review, enrichment, and selective filtering are still needed

---

## Recommended next step

Do not immediately add more prompt variants.

Instead:

1. keep all current candidate batches in the repository
2. perform a lightweight review pass
3. flag suspicious entries
4. only then decide whether to:
   - generate more waves
   - repair suspicious entries
   - enrich metadata
   - create train/dev/test splits

---

## Review priority queue

### Highest priority review
- entries containing `orkgp:HAS_EVALUATION`
- entries containing `orkgp:release`
- complex hard-case entries with nested aggregation or ranking logic

### Medium priority review
- entries with multi-projection outputs
- entries using label-based filtering for semantically important distinctions

### Lower priority review
- straightforward family-anchored lookup questions with clear question–query alignment