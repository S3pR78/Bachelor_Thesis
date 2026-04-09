Auf der Label-Ebene ist die Abdeckung schon ziemlich gut. Über beide Familien hinweg sind alle aktuell im Schema vorgesehenen special_types mindestens einmal vertreten. Praktisch stark vertreten sind vor allem multi_hop, lookup, aggregation, typed_lookup, comparison, temporal, string_operation, multi_intent und count. Schwach vertreten sind dagegen vor allem boolean, negation und missing_info. speziell in nlp4re ist count fast gar nicht vorhanden.


Bei den Query Shapes ist die Abdeckung dagegen deutlich einseitiger: fast alles ist tree, dazu nur wenige chain-Queries und insgesamt nur zwei forest-Fälle; edge, star, cycle und other kommen aktuell gar nicht vor. Aber wenn man SciQA auch betrachtet findet man auch fast nur Trees von da her ich glaube das stellt kein großes Problem dar.


Bei den SPARQL-Komponenten seid ihr solide bei SELECT, FILTER, OPTIONAL, ORDER_BY, GROUP_BY, COUNT, dazu etwas STR, MAX, ASK, NOT_EXISTS, HAVING und UNION. Gar nicht vertreten sind aktuell REGEX, LIMIT, MIN und AVG; IF kommt nur einmal vor, und BIND ebenfalls nur einmal. Das muss ich definitive erweitern.

Bei den Answer Types gibt es nur mixed, list und boolean. Nicht vorhanden sind aktuell direkte resource-, string-, number- oder date-Antworttypen. Das ist für die spätere Evaluation wichtig, weil man sonst viele eher tabellarische und komplexe Outputs hat, aber wenige einfache, klar scorbare Zieltypen.


Die Komplexität ist insgesamt brauchbar, aber unbalanciert: empirical_research ist stark in Richtung high complexity verschoben, während nlp4re deutlich balancierter zwischen low/medium/high ist. Beim Risiko-Profil ist fast alles medium oder high bei hallucination_risk. Obwohl die sind Schwelwerte die ich selber definiert habe aber auf jeden Fall soll ich paar Fragen haben die nicht so direkt das Vokabular aus dem Template benutzen.