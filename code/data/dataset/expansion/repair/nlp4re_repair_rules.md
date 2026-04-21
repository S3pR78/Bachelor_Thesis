# NLP4RE Repair Rules

## Current use
This file documents review-first repair rules for generated NLP4RE candidates.

## Current policy
- Do not automatically replace suspicious predicates unless the grounded family path is confirmed.
- Repeated placeholder-style predicates should first be recorded in the dictionary.
- Repair should be conservative:
  - preserve the original query intent
  - preserve family anchoring
  - avoid inventing replacements

## Current suspicious predicates
- `orkgp:HAS_EVALUATION`
- `orkgp:release`

## Repair priority
1. repeated placeholder-style predicates
2. family anchor issues
3. ranking/top-k phrasing mismatches
4. local logic mismatches