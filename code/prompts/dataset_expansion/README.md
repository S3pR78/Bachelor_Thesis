Current active workflow:

1. assemble prompt from:
   - family base prompt
   - wrapper
   - run file
2. generate minimal candidate JSON with only:
   - id
   - question
   - gold_sparql
   - family
   - answer_type
3. run duplicate/schema checks
4. enrich metadata later in a separate step
5. The `final/` directory is currently archival/reference only.
The active generation path uses `wrappers/`, `runs/`, `scaled_runs/`, and the assembly tool.