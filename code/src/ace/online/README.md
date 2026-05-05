# Online ACE

Online ACE is the per-question adaptive workflow. For each question, the
current context is used to generate and evaluate a query. If the attempt fails,
a reflector proposes one small rule, the in-memory context is updated, and the
same question is retried with that updated context before moving on.

This differs from offline ACE-style playbook construction, where a full
evaluation run is analyzed only after completion and context rules are derived
afterward.

The implementation is intentionally being added in small steps. This package is
the home for the online loop, dataset selection, context management, reflection,
trace writing, and cost tracking.

