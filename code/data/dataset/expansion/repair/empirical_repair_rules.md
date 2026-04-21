# Empirical Research Practice Repair Rules

## Current use
This file documents review-first repair rules for generated empirical_research_practice candidates.

## Current policy
- No automatic predicate replacement unless a repeated suspicious pattern is confirmed.
- Prefer review over repair when only a single candidate is affected.
- Add dictionary entries only when the same suspicious predicate recurs.

## Current known issue pattern
- isolated logic mismatch candidates
- no confirmed repeated placeholder predicate yet

## Repair priority
1. logic mismatches
2. family anchor issues
3. repeated suspicious predicates if they emerge later