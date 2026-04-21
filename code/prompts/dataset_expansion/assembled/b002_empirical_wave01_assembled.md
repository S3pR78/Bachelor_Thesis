# Assembled Dataset Expansion Prompt

## Family Base Prompt
# ORKG SPARQL Generator

Generate precise, executable SPARQL for the Open Research Knowledge Graph. Template: "Empirical Research Practice" (ID: R186491).

## Prefixes (required in every query)
```sparql
PREFIX orkgr: <http://orkg.org/orkg/resource/>
PREFIX orkgc: <http://orkg.org/orkg/class/>
PREFIX orkgp: <http://orkg.org/orkg/predicate/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
```

## Core
| Entity | Term | Usage |
|--------|------|--------|
| Paper | - | publication resource |
| Contribution | `orkgp:P31`, `orkgc:C27001` | `?paper orkgp:P31 ?contribution` ; `?contribution a orkgc:C27001 .` |
| Year (if time/trends) | `orkgp:P29` | `?paper orkgp:P29 ?year` (never on contribution) |
| Venue (if asked) | `orkgp:P135046` | `?contribution orkgp:P135046 ?venue . ?venue rdfs:label ?venue_name` |

#### Template Properties

| Concept | ORKG Term | Type | Description & Usage |
|---------|-----------|------|---------------------|
| venue serie | `orkgp:P135046` | Predicate | In which conference venue is the publication published?. Usage: `?variable orkgp:P135046 ?target` |
| Problem | `orkgp:P32` | Predicate | What is the research problem under consideration in the publication?. Usage: `?variable orkgp:P32 ?target` |
| └─ description | `orkgp:description` | Predicate | description. Usage: `?contribution orkgp:P32 ?subtemplate . ?subtemplate orkgp:description ?subtarget` |
| └─ same as | `orkgp:SAME_AS` | Predicate (multiple) | same as. Usage: `?contribution orkgp:P32 ?subtemplate . ?subtemplate orkgp:SAME_AS ?subtarget` |
| └─ Problem | `orkgp:subProblem` | Predicate (multiple) | Sub Problem. Usage: `?contribution orkgp:P32 ?subtemplate . ?subtemplate orkgp:subProblem ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ description | `orkgp:description` | Predicate | description. Usage: `?contribution orkgp:P32 ?subtemplate . ?subtemplate orkgp:subProblem ?nestedtemplate . ?nestedtemplate orkgp:description ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ same as | `orkgp:SAME_AS` | Predicate (multiple) | same as. Usage: `?contribution orkgp:P32 ?subtemplate . ?subtemplate orkgp:subProblem ?nestedtemplate . ?nestedtemplate orkgp:SAME_AS ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ Problem | `orkgp:subProblem` | Predicate (multiple) | Sub Problem. Usage: `?contribution orkgp:P32 ?subtemplate . ?subtemplate orkgp:subProblem ?nestedtemplate . ?nestedtemplate orkgp:subProblem ?nestedtarget` |
| research paradigm | `orkgp:P57003` | Predicate | What is the underlying research paradigm of the publication?. Usage: `?variable orkgp:P57003 ?target` |
| research question | `orkgp:P37330` | Predicate (multiple) | What is the research question reported in the publication?. Usage: `?variable orkgp:P37330 ?target` |
| └─ question | `orkgp:P44139` | Predicate | What is the research question reported in the publication?. Usage: `?contribution orkgp:P37330 ?subtemplate . ?subtemplate orkgp:P44139 ?subtarget` |
| └─ hidden in text | `orkgp:P55038` | Predicate | Is the research question reported in the publication hidden in the text?. Usage: `?contribution orkgp:P37330 ?subtemplate . ?subtemplate orkgp:P55038 ?subtarget` |
| └─ highlighted in text | `orkgp:P55039` | Predicate | Is the research question reported in the publication highlighted in the text?. Usage: `?contribution orkgp:P37330 ?subtemplate . ?subtemplate orkgp:P55039 ?subtarget` |
| └─ question type | `orkgp:P41928` | Predicate | What is the type of the research question?. Usage: `?contribution orkgp:P37330 ?subtemplate . ?subtemplate orkgp:P41928 ?subtarget` |
| └─ subquestion | `orkgp:P57000` | Predicate (multiple) | What is the subquestion of the research question reported in the publication?. Usage: `?contribution orkgp:P37330 ?subtemplate . ?subtemplate orkgp:P57000 ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ question | `orkgp:P44139` | Predicate | What is the subquestion of the research question reported in the publication?. Usage: `?contribution orkgp:P37330 ?subtemplate . ?subtemplate orkgp:P57000 ?nestedtemplate . ?nestedtemplate orkgp:P44139 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ question type | `orkgp:P41928` | Predicate | What is the type of the sub question?. Usage: `?contribution orkgp:P37330 ?subtemplate . ?subtemplate orkgp:P57000 ?nestedtemplate . ?nestedtemplate orkgp:P41928 ?nestedtarget` |
| research question answer | `orkgp:P57004` | Predicate | How is the answer to the research question reported in the publication?. Usage: `?variable orkgp:P57004 ?target` |
| └─ hidden in text | `orkgp:P55038` | Predicate | Is the answer to the research question reported in the publication hidden in the text?. Usage: `?contribution orkgp:P57004 ?subtemplate . ?subtemplate orkgp:P55038 ?subtarget` |
| └─ highlighted in text | `orkgp:P55039` | Predicate | Is the answer to the research question reported in the publication highlighted in the text?. Usage: `?contribution orkgp:P57004 ?subtemplate . ?subtemplate orkgp:P55039 ?subtarget` |
| data collection | `orkgp:P56008` | Predicate | What is reported about the data collection in the publication?. Usage: `?variable orkgp:P56008 ?target` |
| └─ research data | `orkgp:DATA` | Predicate | What is reported about the collected data in the publication?. Usage: `?contribution orkgp:P56008 ?subtemplate . ?subtemplate orkgp:DATA ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ data type | `orkgp:P7055` | Predicate | What is the type of the collected data reported in the publication?. Usage: `?contribution orkgp:P56008 ?subtemplate . ?subtemplate orkgp:DATA ?nestedtemplate . ?nestedtemplate orkgp:P7055 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ url | `orkgp:url` | Predicate (multiple) | Under which URL(s) can the data be found?. Usage: `?contribution orkgp:P56008 ?subtemplate . ?subtemplate orkgp:DATA ?nestedtemplate . ?nestedtemplate orkgp:url ?nestedtarget` |
| └─ data collection method | `orkgp:P1005` | Predicate (multiple) | What is the data collection method reported in the publication?. Usage: `?contribution orkgp:P56008 ?subtemplate . ?subtemplate orkgp:P1005 ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ method type | `orkgp:P94003` | Predicate | What is the type of method is used for data collection in the publication?. Usage: `?contribution orkgp:P56008 ?subtemplate . ?subtemplate orkgp:P1005 ?nestedtemplate . ?nestedtemplate orkgp:P94003 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ method name | `orkgp:P145012` | Predicate | What is the exact name of the method for data collection reported in the publication?. Usage: `?contribution orkgp:P56008 ?subtemplate . ?subtemplate orkgp:P1005 ?nestedtemplate . ?nestedtemplate orkgp:P145012 ?nestedtarget` |
| data analysis | `orkgp:P15124` | Predicate | What is reported about the data analysis in the publication?. Usage: `?variable orkgp:P15124 ?target` |
| └─ Method | `orkgp:P1005` | Predicate (multiple) | What is the data analysis method reported in the publication?. Usage: `?contribution orkgp:P15124 ?subtemplate . ?subtemplate orkgp:P1005 ?subtarget` |
| └─ inferential statistics | `orkgp:P56043` | Predicate (multiple) | What is reported about inferential statistics used for data analysis in the publication?. Usage: `?contribution orkgp:P15124 ?subtemplate . ?subtemplate orkgp:P56043 ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ Hypothesis | `orkgp:P30001` | Predicate (multiple) | What hypothesis is reported in the publication?. Usage: `?contribution orkgp:P15124 ?subtemplate . ?subtemplate orkgp:P56043 ?nestedtemplate . ?nestedtemplate orkgp:P30001 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ Statistical Technique | `orkgp:P35133` | Predicate (multiple) | What statistical tests is reported in the publication?. Usage: `?contribution orkgp:P15124 ?subtemplate . ?subtemplate orkgp:P56043 ?nestedtemplate . ?nestedtemplate orkgp:P35133 ?nestedtarget` |
| └─ descriptive statistic | `orkgp:P56048` | Predicate (multiple) | What is reported about descriptive statistics used for data analysis in the publication?. Usage: `?contribution orkgp:P15124 ?subtemplate . ?subtemplate orkgp:P56048 ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ measures of frequency | `orkgp:P56049` | Predicate | What measures of frequency are reported in the publication?. Usage: `?contribution orkgp:P15124 ?subtemplate . ?subtemplate orkgp:P56048 ?nestedtemplate . ?nestedtemplate orkgp:P56049 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ measures of central tendency | `orkgp:P57005` | Predicate | What measures of central tendency are reported in the publication?. Usage: `?contribution orkgp:P15124 ?subtemplate . ?subtemplate orkgp:P56048 ?nestedtemplate . ?nestedtemplate orkgp:P57005 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ measures of dispersion or variation | `orkgp:P57008` | Predicate | What measures of dispersion or variation are reported in the publication?. Usage: `?contribution orkgp:P15124 ?subtemplate . ?subtemplate orkgp:P56048 ?nestedtemplate . ?nestedtemplate orkgp:P57008 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ measures of position | `orkgp:P57010` | Predicate | What measures of position are reported in the publication?. Usage: `?contribution orkgp:P15124 ?subtemplate . ?subtemplate orkgp:P56048 ?nestedtemplate . ?nestedtemplate orkgp:P57010 ?nestedtarget` |
| └─ machine learning | `orkgp:P57016` | Predicate (multiple) | What is reported about machine learing used for data analysis in the publication?. Usage: `?contribution orkgp:P15124 ?subtemplate . ?subtemplate orkgp:P57016 ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ Metric | `orkgp:P2006` | Predicate | What metrics are reported for the machine learning reported in the publication?. Usage: `?contribution orkgp:P15124 ?subtemplate . ?subtemplate orkgp:P57016 ?nestedtemplate . ?nestedtemplate orkgp:P2006 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ Machine learning algorithm | `orkgp:P2001` | Predicate (multiple) | What machine learning algorithms are reported in the publication?. Usage: `?contribution orkgp:P15124 ?subtemplate . ?subtemplate orkgp:P57016 ?nestedtemplate . ?nestedtemplate orkgp:P2001 ?nestedtarget` |
| threats to validity | `orkgp:P39099` | Predicate | What threats to validity are reported in a publication?. Usage: `?variable orkgp:P39099 ?target` |
| └─ construct validity | `orkgp:P55037` | Predicate | Are threats to construct validity reported?. Usage: `?contribution orkgp:P39099 ?subtemplate . ?subtemplate orkgp:P55037 ?subtarget` |
| └─ internal validity | `orkgp:P55035` | Predicate | Are threats to internal validity reported?. Usage: `?contribution orkgp:P39099 ?subtemplate . ?subtemplate orkgp:P55035 ?subtarget` |
| └─ external validity | `orkgp:P55034` | Predicate | Are threats to external validity reported?. Usage: `?contribution orkgp:P39099 ?subtemplate . ?subtemplate orkgp:P55034 ?subtarget` |
| └─ conclusion validity | `orkgp:P55036` | Predicate | Are threats to conclusion validity reported?. Usage: `?contribution orkgp:P39099 ?subtemplate . ?subtemplate orkgp:P55036 ?subtarget` |
| └─ reliability | `orkgp:P59109` | Predicate | Are threats to reliability reported?. Usage: `?contribution orkgp:P39099 ?subtemplate . ?subtemplate orkgp:P59109 ?subtarget` |
| └─ generalizability | `orkgp:P60006` | Predicate | Are threats to generalizability reported?. Usage: `?contribution orkgp:P39099 ?subtemplate . ?subtemplate orkgp:P60006 ?subtarget` |
| └─ repeatability | `orkgp:P97002` | Predicate | Are threats to repeatability reported?. Usage: `?contribution orkgp:P39099 ?subtemplate . ?subtemplate orkgp:P97002 ?subtarget` |
| └─ content validity | `orkgp:P68005` | Predicate | Are threats to content validity reported?. Usage: `?contribution orkgp:P39099 ?subtemplate . ?subtemplate orkgp:P68005 ?subtarget` |
| └─ descriptive validity | `orkgp:P97000` | Predicate | Are threats to descriptive validity reported?. Usage: `?contribution orkgp:P39099 ?subtemplate . ?subtemplate orkgp:P97000 ?subtarget` |
| └─ theoretical validity | `orkgp:P97001` | Predicate | Are threats to theoretical validity reported?. Usage: `?contribution orkgp:P39099 ?subtemplate . ?subtemplate orkgp:P97001 ?subtarget` |
| └─ mentioned | `orkgp:P145000` | Predicate | Are threats to validity mentioned but not classified?. Usage: `?contribution orkgp:P39099 ?subtemplate . ?subtemplate orkgp:P145000 ?subtarget` |
| description | `orkgp:description` | Predicate | description. Usage: `?variable orkgp:description ?target` |
| same as | `orkgp:SAME_AS` | Predicate (multiple) | same as. Usage: `?variable orkgp:SAME_AS ?target` |
| Problem | `orkgp:subProblem` | Predicate (multiple) | Sub Problem. Usage: `?variable orkgp:subProblem ?target` |
| └─ description | `orkgp:description` | Predicate | description. Usage: `?contribution orkgp:subProblem ?subtemplate . ?subtemplate orkgp:description ?subtarget` |
| └─ same as | `orkgp:SAME_AS` | Predicate (multiple) | same as. Usage: `?contribution orkgp:subProblem ?subtemplate . ?subtemplate orkgp:SAME_AS ?subtarget` |
| └─ Problem | `orkgp:subProblem` | Predicate (multiple) | Sub Problem. Usage: `?contribution orkgp:subProblem ?subtemplate . ?subtemplate orkgp:subProblem ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ description | `orkgp:description` | Predicate | description. Usage: `?contribution orkgp:subProblem ?subtemplate . ?subtemplate orkgp:subProblem ?nestedtemplate . ?nestedtemplate orkgp:description ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ same as | `orkgp:SAME_AS` | Predicate (multiple) | same as. Usage: `?contribution orkgp:subProblem ?subtemplate . ?subtemplate orkgp:subProblem ?nestedtemplate . ?nestedtemplate orkgp:SAME_AS ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ Problem | `orkgp:subProblem` | Predicate (multiple) | Sub Problem. Usage: `?contribution orkgp:subProblem ?subtemplate . ?subtemplate orkgp:subProblem ?nestedtemplate . ?nestedtemplate orkgp:subProblem ?nestedtarget` |
| question | `orkgp:P44139` | Predicate | What is the subquestion of the research question reported in the publication?. Usage: `?variable orkgp:P44139 ?target` |
| hidden in text | `orkgp:P55038` | Predicate | Is the answer to the research question reported in the publication hidden in the text?. Usage: `?variable orkgp:P55038 ?target` |
| highlighted in text | `orkgp:P55039` | Predicate | Is the answer to the research question reported in the publication highlighted in the text?. Usage: `?variable orkgp:P55039 ?target` |
| question type | `orkgp:P41928` | Predicate | What is the type of the sub question?. Usage: `?variable orkgp:P41928 ?target` |
| subquestion | `orkgp:P57000` | Predicate (multiple) | What is the subquestion of the research question reported in the publication?. Usage: `?variable orkgp:P57000 ?target` |
| └─ question | `orkgp:P44139` | Predicate | What is the subquestion of the research question reported in the publication?. Usage: `?contribution orkgp:P57000 ?subtemplate . ?subtemplate orkgp:P44139 ?subtarget` |
| └─ question type | `orkgp:P41928` | Predicate | What is the type of the sub question?. Usage: `?contribution orkgp:P57000 ?subtemplate . ?subtemplate orkgp:P41928 ?subtarget` |
| research data | `orkgp:DATA` | Predicate | What is reported about the collected data in the publication?. Usage: `?variable orkgp:DATA ?target` |
| └─ data type | `orkgp:P7055` | Predicate | What is the type of the collected data reported in the publication?. Usage: `?contribution orkgp:DATA ?subtemplate . ?subtemplate orkgp:P7055 ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ qualitative  | `orkgp:P57038` | Predicate | Is the collected data reported in the publication qualitative?. Usage: `?contribution orkgp:DATA ?subtemplate . ?subtemplate orkgp:P7055 ?nestedtemplate . ?nestedtemplate orkgp:P57038 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ quantitative  | `orkgp:P57039` | Predicate | Is the collected data reported in the publication quantitative?. Usage: `?contribution orkgp:DATA ?subtemplate . ?subtemplate orkgp:P7055 ?nestedtemplate . ?nestedtemplate orkgp:P57039 ?nestedtarget` |
| └─ url | `orkgp:url` | Predicate (multiple) | Under which URL(s) can the data be found?. Usage: `?contribution orkgp:DATA ?subtemplate . ?subtemplate orkgp:url ?subtarget` |
| Method | `orkgp:P1005` | Predicate (multiple) | What is the data analysis method reported in the publication?. Usage: `?variable orkgp:P1005 ?target` |
| data type | `orkgp:P7055` | Predicate | What is the type of the collected data reported in the publication?. Usage: `?variable orkgp:P7055 ?target` |
| └─ qualitative  | `orkgp:P57038` | Predicate | Is the collected data reported in the publication qualitative?. Usage: `?contribution orkgp:P7055 ?subtemplate . ?subtemplate orkgp:P57038 ?subtarget` |
| └─ quantitative  | `orkgp:P57039` | Predicate | Is the collected data reported in the publication quantitative?. Usage: `?contribution orkgp:P7055 ?subtemplate . ?subtemplate orkgp:P57039 ?subtarget` |
| url | `orkgp:url` | Predicate (multiple) | Under which URL(s) can the data be found?. Usage: `?variable orkgp:url ?target` |
| qualitative  | `orkgp:P57038` | Predicate | Is the collected data reported in the publication qualitative?. Usage: `?variable orkgp:P57038 ?target` |
| quantitative  | `orkgp:P57039` | Predicate | Is the collected data reported in the publication quantitative?. Usage: `?variable orkgp:P57039 ?target` |
| method type | `orkgp:P94003` | Predicate | What is the type of method is used for data collection in the publication?. Usage: `?variable orkgp:P94003 ?target` |
| method name | `orkgp:P145012` | Predicate | What is the exact name of the method for data collection reported in the publication?. Usage: `?variable orkgp:P145012 ?target` |
| inferential statistics | `orkgp:P56043` | Predicate (multiple) | What is reported about inferential statistics used for data analysis in the publication?. Usage: `?variable orkgp:P56043 ?target` |
| └─ Hypothesis | `orkgp:P30001` | Predicate (multiple) | What hypothesis is reported in the publication?. Usage: `?contribution orkgp:P56043 ?subtemplate . ?subtemplate orkgp:P30001 ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ hypothesis statement | `orkgp:P56046` | Predicate | What hypothesis statement is reported in the publication?. Usage: `?contribution orkgp:P56043 ?subtemplate . ?subtemplate orkgp:P30001 ?nestedtemplate . ?nestedtemplate orkgp:P56046 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ hypothesis type | `orkgp:P41703` | Predicate | What is the type of the hypothesis reported in the publication?. Usage: `?contribution orkgp:P56043 ?subtemplate . ?subtemplate orkgp:P30001 ?nestedtemplate . ?nestedtemplate orkgp:P41703 ?nestedtarget` |
| └─ Statistical Technique | `orkgp:P35133` | Predicate (multiple) | What statistical tests is reported in the publication?. Usage: `?contribution orkgp:P56043 ?subtemplate . ?subtemplate orkgp:P35133 ?subtarget` |
| descriptive statistic | `orkgp:P56048` | Predicate (multiple) | What is reported about descriptive statistics used for data analysis in the publication?. Usage: `?variable orkgp:P56048 ?target` |
| └─ measures of frequency | `orkgp:P56049` | Predicate | What measures of frequency are reported in the publication?. Usage: `?contribution orkgp:P56048 ?subtemplate . ?subtemplate orkgp:P56049 ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ count | `orkgp:P55023` | Predicate | Is count as a measure of frequency reported in the publication?. Usage: `?contribution orkgp:P56048 ?subtemplate . ?subtemplate orkgp:P56049 ?nestedtemplate . ?nestedtemplate orkgp:P55023 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ percent | `orkgp:P56050` | Predicate | Is percent as a measure of frequency reported in the publication?. Usage: `?contribution orkgp:P56048 ?subtemplate . ?subtemplate orkgp:P56049 ?nestedtemplate . ?nestedtemplate orkgp:P56050 ?nestedtarget` |
| └─ measures of central tendency | `orkgp:P57005` | Predicate | What measures of central tendency are reported in the publication?. Usage: `?contribution orkgp:P56048 ?subtemplate . ?subtemplate orkgp:P57005 ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ mean | `orkgp:P47000` | Predicate | Is mean as a measure of central tendency reported in the publication?. Usage: `?contribution orkgp:P56048 ?subtemplate . ?subtemplate orkgp:P57005 ?nestedtemplate . ?nestedtemplate orkgp:P47000 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ median | `orkgp:P57006` | Predicate | Is median as a measure of central tendency reported in the publication?. Usage: `?contribution orkgp:P56048 ?subtemplate . ?subtemplate orkgp:P57005 ?nestedtemplate . ?nestedtemplate orkgp:P57006 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ mode | `orkgp:P57007` | Predicate | Is mode as a measure of central tendency reported in the publication?. Usage: `?contribution orkgp:P56048 ?subtemplate . ?subtemplate orkgp:P57005 ?nestedtemplate . ?nestedtemplate orkgp:P57007 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ minimum | `orkgp:P44107` | Predicate | Is minimum as a measure of central tendency reported in the publication?. Usage: `?contribution orkgp:P56048 ?subtemplate . ?subtemplate orkgp:P57005 ?nestedtemplate . ?nestedtemplate orkgp:P44107 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ maximum | `orkgp:P44108` | Predicate | Is maximum as a measure of central tendency reported in the publication?. Usage: `?contribution orkgp:P56048 ?subtemplate . ?subtemplate orkgp:P57005 ?nestedtemplate . ?nestedtemplate orkgp:P44108 ?nestedtarget` |
| └─ measures of dispersion or variation | `orkgp:P57008` | Predicate | What measures of dispersion or variation are reported in the publication?. Usage: `?contribution orkgp:P56048 ?subtemplate . ?subtemplate orkgp:P57008 ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ range | `orkgp:P4013` | Predicate | Is range as a measure of dispersion or variation reported in the publication?. Usage: `?contribution orkgp:P56048 ?subtemplate . ?subtemplate orkgp:P57008 ?nestedtemplate . ?nestedtemplate orkgp:P4013 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ variance | `orkgp:P57009` | Predicate | Is variance as a measure of dispersion or variation reported in the publication?. Usage: `?contribution orkgp:P56048 ?subtemplate . ?subtemplate orkgp:P57008 ?nestedtemplate . ?nestedtemplate orkgp:P57009 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ standard deviation | `orkgp:P44087` | Predicate | Is standard deviation as a measure of dispersion or variation reported in the publication?. Usage: `?contribution orkgp:P56048 ?subtemplate . ?subtemplate orkgp:P57008 ?nestedtemplate . ?nestedtemplate orkgp:P44087 ?nestedtarget` |
| └─ measures of position | `orkgp:P57010` | Predicate | What measures of position are reported in the publication?. Usage: `?contribution orkgp:P56048 ?subtemplate . ?subtemplate orkgp:P57010 ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ boxplot | `orkgp:P59065` | Predicate | Is boxplot reported in the publication?. Usage: `?contribution orkgp:P56048 ?subtemplate . ?subtemplate orkgp:P57010 ?nestedtemplate . ?nestedtemplate orkgp:P59065 ?nestedtarget` |
| machine learning | `orkgp:P57016` | Predicate (multiple) | What is reported about machine learing used for data analysis in the publication?. Usage: `?variable orkgp:P57016 ?target` |
| └─ Metric | `orkgp:P2006` | Predicate | What metrics are reported for the machine learning reported in the publication?. Usage: `?contribution orkgp:P57016 ?subtemplate . ?subtemplate orkgp:P2006 ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ recall | `orkgp:P5073` | Predicate | Is recall reported in the publication?. Usage: `?contribution orkgp:P57016 ?subtemplate . ?subtemplate orkgp:P2006 ?nestedtemplate . ?nestedtemplate orkgp:P5073 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ precision | `orkgp:P3004` | Predicate | Is precision reported in the publication?. Usage: `?contribution orkgp:P57016 ?subtemplate . ?subtemplate orkgp:P2006 ?nestedtemplate . ?nestedtemplate orkgp:P3004 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ accuracy | `orkgp:P18048` | Predicate | Is accuracy reported in the publication?. Usage: `?contribution orkgp:P57016 ?subtemplate . ?subtemplate orkgp:P2006 ?nestedtemplate . ?nestedtemplate orkgp:P18048 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ f-score | `orkgp:P59137` | Predicate | Is f-score reported in the publication?. Usage: `?contribution orkgp:P57016 ?subtemplate . ?subtemplate orkgp:P2006 ?nestedtemplate . ?nestedtemplate orkgp:P59137 ?nestedtarget` |
| └─ Machine learning algorithm | `orkgp:P2001` | Predicate (multiple) | What machine learning algorithms are reported in the publication?. Usage: `?contribution orkgp:P57016 ?subtemplate . ?subtemplate orkgp:P2001 ?subtarget` |
| Hypothesis | `orkgp:P30001` | Predicate (multiple) | What hypothesis is reported in the publication?. Usage: `?variable orkgp:P30001 ?target` |
| └─ hypothesis statement | `orkgp:P56046` | Predicate | What hypothesis statement is reported in the publication?. Usage: `?contribution orkgp:P30001 ?subtemplate . ?subtemplate orkgp:P56046 ?subtarget` |
| └─ hypothesis type | `orkgp:P41703` | Predicate | What is the type of the hypothesis reported in the publication?. Usage: `?contribution orkgp:P30001 ?subtemplate . ?subtemplate orkgp:P41703 ?subtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ Null hypothesis | `orkgp:P35106` | Predicate | Is the reported hypothesis the null hypothesis?. Usage: `?contribution orkgp:P30001 ?subtemplate . ?subtemplate orkgp:P41703 ?nestedtemplate . ?nestedtemplate orkgp:P35106 ?nestedtarget` |
| &nbsp;&nbsp;&nbsp;&nbsp;└─ Alternative hypothesis | `orkgp:P35107` | Predicate | Is the reported hypothesis the alternative hypothesis?. Usage: `?contribution orkgp:P30001 ?subtemplate . ?subtemplate orkgp:P41703 ?nestedtemplate . ?nestedtemplate orkgp:P35107 ?nestedtarget` |
| Statistical Technique | `orkgp:P35133` | Predicate (multiple) | What statistical tests is reported in the publication?. Usage: `?variable orkgp:P35133 ?target` |
| hypothesis statement | `orkgp:P56046` | Predicate | What hypothesis statement is reported in the publication?. Usage: `?variable orkgp:P56046 ?target` |
| hypothesis type | `orkgp:P41703` | Predicate | What is the type of the hypothesis reported in the publication?. Usage: `?variable orkgp:P41703 ?target` |
| └─ Null hypothesis | `orkgp:P35106` | Predicate | Is the reported hypothesis the null hypothesis?. Usage: `?contribution orkgp:P41703 ?subtemplate . ?subtemplate orkgp:P35106 ?subtarget` |
| └─ Alternative hypothesis | `orkgp:P35107` | Predicate | Is the reported hypothesis the alternative hypothesis?. Usage: `?contribution orkgp:P41703 ?subtemplate . ?subtemplate orkgp:P35107 ?subtarget` |
| Null hypothesis | `orkgp:P35106` | Predicate | Is the reported hypothesis the null hypothesis?. Usage: `?variable orkgp:P35106 ?target` |
| Alternative hypothesis | `orkgp:P35107` | Predicate | Is the reported hypothesis the alternative hypothesis?. Usage: `?variable orkgp:P35107 ?target` |
| measures of frequency | `orkgp:P56049` | Predicate | What measures of frequency are reported in the publication?. Usage: `?variable orkgp:P56049 ?target` |
| └─ count | `orkgp:P55023` | Predicate | Is count as a measure of frequency reported in the publication?. Usage: `?contribution orkgp:P56049 ?subtemplate . ?subtemplate orkgp:P55023 ?subtarget` |
| └─ percent | `orkgp:P56050` | Predicate | Is percent as a measure of frequency reported in the publication?. Usage: `?contribution orkgp:P56049 ?subtemplate . ?subtemplate orkgp:P56050 ?subtarget` |
| measures of central tendency | `orkgp:P57005` | Predicate | What measures of central tendency are reported in the publication?. Usage: `?variable orkgp:P57005 ?target` |
| └─ mean | `orkgp:P47000` | Predicate | Is mean as a measure of central tendency reported in the publication?. Usage: `?contribution orkgp:P57005 ?subtemplate . ?subtemplate orkgp:P47000 ?subtarget` |
| └─ median | `orkgp:P57006` | Predicate | Is median as a measure of central tendency reported in the publication?. Usage: `?contribution orkgp:P57005 ?subtemplate . ?subtemplate orkgp:P57006 ?subtarget` |
| └─ mode | `orkgp:P57007` | Predicate | Is mode as a measure of central tendency reported in the publication?. Usage: `?contribution orkgp:P57005 ?subtemplate . ?subtemplate orkgp:P57007 ?subtarget` |
| └─ minimum | `orkgp:P44107` | Predicate | Is minimum as a measure of central tendency reported in the publication?. Usage: `?contribution orkgp:P57005 ?subtemplate . ?subtemplate orkgp:P44107 ?subtarget` |
| └─ maximum | `orkgp:P44108` | Predicate | Is maximum as a measure of central tendency reported in the publication?. Usage: `?contribution orkgp:P57005 ?subtemplate . ?subtemplate orkgp:P44108 ?subtarget` |
| measures of dispersion or variation | `orkgp:P57008` | Predicate | What measures of dispersion or variation are reported in the publication?. Usage: `?variable orkgp:P57008 ?target` |
| └─ range | `orkgp:P4013` | Predicate | Is range as a measure of dispersion or variation reported in the publication?. Usage: `?contribution orkgp:P57008 ?subtemplate . ?subtemplate orkgp:P4013 ?subtarget` |
| └─ variance | `orkgp:P57009` | Predicate | Is variance as a measure of dispersion or variation reported in the publication?. Usage: `?contribution orkgp:P57008 ?subtemplate . ?subtemplate orkgp:P57009 ?subtarget` |
| └─ standard deviation | `orkgp:P44087` | Predicate | Is standard deviation as a measure of dispersion or variation reported in the publication?. Usage: `?contribution orkgp:P57008 ?subtemplate . ?subtemplate orkgp:P44087 ?subtarget` |
| measures of position | `orkgp:P57010` | Predicate | What measures of position are reported in the publication?. Usage: `?variable orkgp:P57010 ?target` |
| └─ boxplot | `orkgp:P59065` | Predicate | Is boxplot reported in the publication?. Usage: `?contribution orkgp:P57010 ?subtemplate . ?subtemplate orkgp:P59065 ?subtarget` |
| count | `orkgp:P55023` | Predicate | Is count as a measure of frequency reported in the publication?. Usage: `?variable orkgp:P55023 ?target` |
| percent | `orkgp:P56050` | Predicate | Is percent as a measure of frequency reported in the publication?. Usage: `?variable orkgp:P56050 ?target` |
| mean | `orkgp:P47000` | Predicate | Is mean as a measure of central tendency reported in the publication?. Usage: `?variable orkgp:P47000 ?target` |
| median | `orkgp:P57006` | Predicate | Is median as a measure of central tendency reported in the publication?. Usage: `?variable orkgp:P57006 ?target` |
| mode | `orkgp:P57007` | Predicate | Is mode as a measure of central tendency reported in the publication?. Usage: `?variable orkgp:P57007 ?target` |
| minimum | `orkgp:P44107` | Predicate | Is minimum as a measure of central tendency reported in the publication?. Usage: `?variable orkgp:P44107 ?target` |
| maximum | `orkgp:P44108` | Predicate | Is maximum as a measure of central tendency reported in the publication?. Usage: `?variable orkgp:P44108 ?target` |
| range | `orkgp:P4013` | Predicate | Is range as a measure of dispersion or variation reported in the publication?. Usage: `?variable orkgp:P4013 ?target` |
| variance | `orkgp:P57009` | Predicate | Is variance as a measure of dispersion or variation reported in the publication?. Usage: `?variable orkgp:P57009 ?target` |
| standard deviation | `orkgp:P44087` | Predicate | Is standard deviation as a measure of dispersion or variation reported in the publication?. Usage: `?variable orkgp:P44087 ?target` |
| boxplot | `orkgp:P59065` | Predicate | Is boxplot reported in the publication?. Usage: `?variable orkgp:P59065 ?target` |
| Metric | `orkgp:P2006` | Predicate | What metrics are reported for the machine learning reported in the publication?. Usage: `?variable orkgp:P2006 ?target` |
| └─ recall | `orkgp:P5073` | Predicate | Is recall reported in the publication?. Usage: `?contribution orkgp:P2006 ?subtemplate . ?subtemplate orkgp:P5073 ?subtarget` |
| └─ precision | `orkgp:P3004` | Predicate | Is precision reported in the publication?. Usage: `?contribution orkgp:P2006 ?subtemplate . ?subtemplate orkgp:P3004 ?subtarget` |
| └─ accuracy | `orkgp:P18048` | Predicate | Is accuracy reported in the publication?. Usage: `?contribution orkgp:P2006 ?subtemplate . ?subtemplate orkgp:P18048 ?subtarget` |
| └─ f-score | `orkgp:P59137` | Predicate | Is f-score reported in the publication?. Usage: `?contribution orkgp:P2006 ?subtemplate . ?subtemplate orkgp:P59137 ?subtarget` |
| Machine learning algorithm | `orkgp:P2001` | Predicate (multiple) | What machine learning algorithms are reported in the publication?. Usage: `?variable orkgp:P2001 ?target` |
| recall | `orkgp:P5073` | Predicate | Is recall reported in the publication?. Usage: `?variable orkgp:P5073 ?target` |
| precision | `orkgp:P3004` | Predicate | Is precision reported in the publication?. Usage: `?variable orkgp:P3004 ?target` |
| accuracy | `orkgp:P18048` | Predicate | Is accuracy reported in the publication?. Usage: `?variable orkgp:P18048 ?target` |
| f-score | `orkgp:P59137` | Predicate | Is f-score reported in the publication?. Usage: `?variable orkgp:P59137 ?target` |
| construct validity | `orkgp:P55037` | Predicate | Are threats to construct validity reported?. Usage: `?variable orkgp:P55037 ?target` |
| internal validity | `orkgp:P55035` | Predicate | Are threats to internal validity reported?. Usage: `?variable orkgp:P55035 ?target` |
| external validity | `orkgp:P55034` | Predicate | Are threats to external validity reported?. Usage: `?variable orkgp:P55034 ?target` |
| conclusion validity | `orkgp:P55036` | Predicate | Are threats to conclusion validity reported?. Usage: `?variable orkgp:P55036 ?target` |
| reliability | `orkgp:P59109` | Predicate | Are threats to reliability reported?. Usage: `?variable orkgp:P59109 ?target` |
| generalizability | `orkgp:P60006` | Predicate | Are threats to generalizability reported?. Usage: `?variable orkgp:P60006 ?target` |
| repeatability | `orkgp:P97002` | Predicate | Are threats to repeatability reported?. Usage: `?variable orkgp:P97002 ?target` |
| content validity | `orkgp:P68005` | Predicate | Are threats to content validity reported?. Usage: `?variable orkgp:P68005 ?target` |
| descriptive validity | `orkgp:P97000` | Predicate | Are threats to descriptive validity reported?. Usage: `?variable orkgp:P97000 ?target` |
| theoretical validity | `orkgp:P97001` | Predicate | Are threats to theoretical validity reported?. Usage: `?variable orkgp:P97001 ?target` |
| mentioned | `orkgp:P145000` | Predicate | Are threats to validity mentioned but not classified?. Usage: `?variable orkgp:P145000 ?target` |


#### Template Hierarchy Structure

Traverse via parent → child:

**venue serie** (`orkgp:P135046`)

**Problem** (`orkgp:P32`)
  └─ **description** (`orkgp:description`)
  └─ **same as** (`orkgp:SAME_AS`)
  └─ **Problem** (`orkgp:subProblem`)
    └─ **description** (`orkgp:description`)
    └─ **same as** (`orkgp:SAME_AS`)
    └─ **Problem** (`orkgp:subProblem`)

**research paradigm** (`orkgp:P57003`)

**research question** (`orkgp:P37330`)
  └─ **question** (`orkgp:P44139`)
  └─ **hidden in text** (`orkgp:P55038`)
  └─ **highlighted in text** (`orkgp:P55039`)
  └─ **question type** (`orkgp:P41928`)
  └─ **subquestion** (`orkgp:P57000`)
    └─ **question** (`orkgp:P44139`)
    └─ **question type** (`orkgp:P41928`)

**research question answer** (`orkgp:P57004`)
  └─ **hidden in text** (`orkgp:P55038`)
  └─ **highlighted in text** (`orkgp:P55039`)

**data collection** (`orkgp:P56008`)
  └─ **research data** (`orkgp:DATA`)
    └─ **data type** (`orkgp:P7055`)
    └─ **url** (`orkgp:url`)
  └─ **data collection method** (`orkgp:P1005`)
    └─ **method type** (`orkgp:P94003`)
    └─ **method name** (`orkgp:P145012`)

**data analysis** (`orkgp:P15124`)
  └─ **Method** (`orkgp:P1005`)
  └─ **inferential statistics** (`orkgp:P56043`)
    └─ **Hypothesis** (`orkgp:P30001`)
    └─ **Statistical Technique** (`orkgp:P35133`)
  └─ **descriptive statistic** (`orkgp:P56048`)
    └─ **measures of frequency** (`orkgp:P56049`)
    └─ **measures of central tendency** (`orkgp:P57005`)
    └─ **measures of dispersion or variation** (`orkgp:P57008`)
    └─ **measures of position** (`orkgp:P57010`)
  └─ **machine learning** (`orkgp:P57016`)
    └─ **Metric** (`orkgp:P2006`)
    └─ **Machine learning algorithm** (`orkgp:P2001`)

**threats to validity** (`orkgp:P39099`)
  └─ **construct validity** (`orkgp:P55037`)
  └─ **internal validity** (`orkgp:P55035`)
  └─ **external validity** (`orkgp:P55034`)
  └─ **conclusion validity** (`orkgp:P55036`)
  └─ **reliability** (`orkgp:P59109`)
  └─ **generalizability** (`orkgp:P60006`)
  └─ **repeatability** (`orkgp:P97002`)
  └─ **content validity** (`orkgp:P68005`)
  └─ **descriptive validity** (`orkgp:P97000`)
  └─ **theoretical validity** (`orkgp:P97001`)
  └─ **mentioned** (`orkgp:P145000`)

**description** (`orkgp:description`)

**same as** (`orkgp:SAME_AS`)

**Problem** (`orkgp:subProblem`)
  └─ **description** (`orkgp:description`)
  └─ **same as** (`orkgp:SAME_AS`)
  └─ **Problem** (`orkgp:subProblem`)
    └─ **description** (`orkgp:description`)
    └─ **same as** (`orkgp:SAME_AS`)
    └─ **Problem** (`orkgp:subProblem`)

**question** (`orkgp:P44139`)

**hidden in text** (`orkgp:P55038`)

**highlighted in text** (`orkgp:P55039`)

**question type** (`orkgp:P41928`)

**subquestion** (`orkgp:P57000`)
  └─ **question** (`orkgp:P44139`)
  └─ **question type** (`orkgp:P41928`)

**research data** (`orkgp:DATA`)
  └─ **data type** (`orkgp:P7055`)
    └─ **qualitative ** (`orkgp:P57038`)
    └─ **quantitative ** (`orkgp:P57039`)
  └─ **url** (`orkgp:url`)

**Method** (`orkgp:P1005`)

**data type** (`orkgp:P7055`)
  └─ **qualitative ** (`orkgp:P57038`)
  └─ **quantitative ** (`orkgp:P57039`)

**url** (`orkgp:url`)

**qualitative ** (`orkgp:P57038`)

**quantitative ** (`orkgp:P57039`)

**method type** (`orkgp:P94003`)

**method name** (`orkgp:P145012`)

**inferential statistics** (`orkgp:P56043`)
  └─ **Hypothesis** (`orkgp:P30001`)
    └─ **hypothesis statement** (`orkgp:P56046`)
    └─ **hypothesis type** (`orkgp:P41703`)
  └─ **Statistical Technique** (`orkgp:P35133`)

**descriptive statistic** (`orkgp:P56048`)
  └─ **measures of frequency** (`orkgp:P56049`)
    └─ **count** (`orkgp:P55023`)
    └─ **percent** (`orkgp:P56050`)
  └─ **measures of central tendency** (`orkgp:P57005`)
    └─ **mean** (`orkgp:P47000`)
    └─ **median** (`orkgp:P57006`)
    └─ **mode** (`orkgp:P57007`)
    └─ **minimum** (`orkgp:P44107`)
    └─ **maximum** (`orkgp:P44108`)
  └─ **measures of dispersion or variation** (`orkgp:P57008`)
    └─ **range** (`orkgp:P4013`)
    └─ **variance** (`orkgp:P57009`)
    └─ **standard deviation** (`orkgp:P44087`)
  └─ **measures of position** (`orkgp:P57010`)
    └─ **boxplot** (`orkgp:P59065`)

**machine learning** (`orkgp:P57016`)
  └─ **Metric** (`orkgp:P2006`)
    └─ **recall** (`orkgp:P5073`)
    └─ **precision** (`orkgp:P3004`)
    └─ **accuracy** (`orkgp:P18048`)
    └─ **f-score** (`orkgp:P59137`)
  └─ **Machine learning algorithm** (`orkgp:P2001`)

**Hypothesis** (`orkgp:P30001`)
  └─ **hypothesis statement** (`orkgp:P56046`)
  └─ **hypothesis type** (`orkgp:P41703`)
    └─ **Null hypothesis** (`orkgp:P35106`)
    └─ **Alternative hypothesis** (`orkgp:P35107`)

**Statistical Technique** (`orkgp:P35133`)

**hypothesis statement** (`orkgp:P56046`)

**hypothesis type** (`orkgp:P41703`)
  └─ **Null hypothesis** (`orkgp:P35106`)
  └─ **Alternative hypothesis** (`orkgp:P35107`)

**Null hypothesis** (`orkgp:P35106`)

**Alternative hypothesis** (`orkgp:P35107`)

**measures of frequency** (`orkgp:P56049`)
  └─ **count** (`orkgp:P55023`)
  └─ **percent** (`orkgp:P56050`)

**measures of central tendency** (`orkgp:P57005`)
  └─ **mean** (`orkgp:P47000`)
  └─ **median** (`orkgp:P57006`)
  └─ **mode** (`orkgp:P57007`)
  └─ **minimum** (`orkgp:P44107`)
  └─ **maximum** (`orkgp:P44108`)

**measures of dispersion or variation** (`orkgp:P57008`)
  └─ **range** (`orkgp:P4013`)
  └─ **variance** (`orkgp:P57009`)
  └─ **standard deviation** (`orkgp:P44087`)

**measures of position** (`orkgp:P57010`)
  └─ **boxplot** (`orkgp:P59065`)

**count** (`orkgp:P55023`)

**percent** (`orkgp:P56050`)

**mean** (`orkgp:P47000`)

**median** (`orkgp:P57006`)

**mode** (`orkgp:P57007`)

**minimum** (`orkgp:P44107`)

**maximum** (`orkgp:P44108`)

**range** (`orkgp:P4013`)

**variance** (`orkgp:P57009`)

**standard deviation** (`orkgp:P44087`)

**boxplot** (`orkgp:P59065`)

**Metric** (`orkgp:P2006`)
  └─ **recall** (`orkgp:P5073`)
  └─ **precision** (`orkgp:P3004`)
  └─ **accuracy** (`orkgp:P18048`)
  └─ **f-score** (`orkgp:P59137`)

**Machine learning algorithm** (`orkgp:P2001`)

**recall** (`orkgp:P5073`)

**precision** (`orkgp:P3004`)

**accuracy** (`orkgp:P18048`)

**f-score** (`orkgp:P59137`)

**construct validity** (`orkgp:P55037`)

**internal validity** (`orkgp:P55035`)

**external validity** (`orkgp:P55034`)

**conclusion validity** (`orkgp:P55036`)

**reliability** (`orkgp:P59109`)

**generalizability** (`orkgp:P60006`)

**repeatability** (`orkgp:P97002`)

**content validity** (`orkgp:P68005`)

**descriptive validity** (`orkgp:P97000`)

**theoretical validity** (`orkgp:P97001`)

**mentioned** (`orkgp:P145000`)

└─ = child of above; traverse parent first.



## Template-Specific Guidance

Empirical study = has data collection (not "no collection"), data analysis (not "no analysis"). Often filter venue = IEEE International Requirements Engineering Conference. Use `?contribution a orkgc:C27001`; return ?dc_label/?da_label and let processing filter.



Exclude non-empirical: `FILTER(LCASE(STR(?dc_label)) != LCASE("no collection"))`, `FILTER(LCASE(STR(?da_label)) != LCASE("no analysis"))`. Venue: `?contribution orkgp:P135046 ?venue . ?venue rdfs:label ?venue_name` then FILTER with LCASE. Method types: traverse contribution → data collection → method → method type → label. Threats: `?contribution orkgp:P39099 ?threats` then OPTIONAL per threat type. Use SAMPLE()+GROUP BY for boolean/dedup.



OPTIONAL for optional props; declare contribution class; traverse to method type for method labels; SAMPLE()+GROUP BY for one row per paper when needed.



Empty methods → traverse to method type (collection→method→method type→label). Venue not working → get `?venue rdfs:label ?venue_name` first. Duplicates → SAMPLE() with GROUP BY.


## Rules
1. **Class**: Always `?contribution a orkgc:C27001 .`
2. **Year**: Only if question asks time/trends; use `?paper orkgp:P29 ?year` (never `?contribution orkgp:P29`).
3. **Top N / frequency**: Include `?paper` and `?paperLabel` in SELECT; no LIMIT; ORDER BY paper.
4. **One query per code block**: Each ```sparql block has one SELECT; use `# id: name`.
5. **URIs vs labels**: Properties return URIs. Get label first: `?resource rdfs:label ?label`. Compare only the label to strings.
6. **Label comparison**: Always use `LCASE(STR(?label)) = LCASE("value")` (case-insensitive).
7. **BIND**: Only in WHERE; variables in BIND must be defined before it. No IF() in SELECT—use BIND(IF(...)) in WHERE.
8. **Proportions**: Use subqueries; cast `xsd:decimal` for division.
9. **Nested props**: Follow schema hierarchy (contribution → parent → child); use `└─` in Template Properties.

**Output**: Only SPARQL in ```sparql blocks. No explanations. One query per block.

## Input
**Research Question:** [Research Question]

---

## Batch Wrapper Prompt
# Wrapper Prompt — B002 Missing Query Components

## Purpose
Generate candidate dataset entries that increase coverage of missing or weak query components.

Primary target components:
- REGEX
- LIMIT
- MIN
- AVG

Secondary optional targets:
- BIND
- UNION
- NOT_EXISTS

## Use rule
This wrapper must be combined with exactly one family-specific base prompt from the repository.

## Hard constraints
1. Do not invent predicates, classes, template fields, or schema paths.
2. Only use query components when they are semantically justified.
3. Do not force artificial complexity just to include an operator.
4. Generate only English questions.
5. Avoid duplicates and near-duplicates.
6. Keep question wording natural and academically plausible.
7. Every query must use at least one family-specific template predicate or template path from the selected family prompt.
8. Do not generate generic bibliographic-only queries based only on title, year, or generic paper metadata.
9. Use REGEX, LIMIT, MIN, AVG, BIND, UNION, or NOT_EXISTS only when semantically justified.
10. Do not insert a target component artificially if it makes the question unnatural.
11. `answer_type` must be one of:
   - `resource`
   - `string`
   - `number`
   - `date`

   Do not use values such as:
   - `factoid`
   - `non_factoid`

### Question-answer alignment rules

1. The natural-language question must match the projected variables in the SPARQL query.
2. If the query returns both `?paper` and an answer variable, the question must explicitly ask for the paper together with the answer.
3. If the question asks only for the answer value, do not project `?paper` unless it is required by the question.
4. Avoid underspecified wording such as:
   - "the study"
   - "the dataset"
   - "the paper"
   unless the question includes a clear identifying constraint.
5. Prefer formulations such as:
   - "Which papers ..."
   - "For which papers ..."
   - "Which datasets ..."
   - "Which natural languages are reported for datasets ..."
6. Use the family anchor pattern consistently. For NLP4RE, prefer the family grounding structure where the paper links to a contribution and the contribution carries the template class. Do not assign the template class directly to the paper unless the family schema explicitly requires it.


Prefer projecting only the minimal variables needed to answer the question.
Do not include `?paper` or `?paperLabel` unless the question explicitly asks for papers.

## Desired behavior
- include comparison, temporal, and ranking-style questions where helpful
- prefer medium-to-high complexity overall
- ensure metadata reflects the actual query behavior
- `query_components` must match the SPARQL query exactly

## Output fields

Return only these fields for each item:
- `id`
- `question`
- `gold_sparql`
- `family`
- `answer_type`

Do not generate any other metadata fields.
Additional metadata will be added later in a separate enrichment step.

## Output requirement
Return valid JSON only.
Return a JSON object with key `"items"`.

---

## Run Prompt
# Scaled Run Prompt — B002 Empirical Wave 01

Generate exactly 50 candidate dataset entries.

Selected family: `empirical_research_practice`

For every item, set:
- `family` = `empirical_research_practice`

Do not generate an `id` field.
IDs will be assigned later in a deterministic post-processing step.

Primary batch purpose:
- expand coverage of important query components for empirical_research_practice
- generate schema-faithful questions that naturally require component-sensitive SPARQL patterns
- increase coverage of useful operator and constraint combinations

Preferred focus:
- REGEX or string-based filtering where semantically justified
- LIMIT where the question naturally asks for a top result or restricted result set
- MIN / MAX / AVG where aggregation is clearly motivated
- NOT EXISTS where missing-information logic is natural
- comparison and constrained retrieval
- moderate multi-hop behavior

Preferred difficulty:
- mostly medium complexity
- some medium-to-high complexity
- avoid artificial complexity
- avoid operator use for its own sake

Important alignment rules:
- If a query returns a ranked or top-k list, phrase the question accordingly.
- Do not phrase a top-k query as if it returned a single strict maximum unless the query really enforces that.
- Use REGEX, LIMIT, MIN, AVG, MAX, or NOT EXISTS only when genuinely motivated by the question.
- Do not create artificial operator-driven questions just to satisfy the batch purpose.

Target answer_type distribution:
- around 14 `resource`
- around 14 `string`
- around 12 `number`
- around 10 `date`

Avoid overlap with:
- seed benchmark entries
- previously accepted or retained `b002_empirical` candidates
- earlier generated candidates in the same family
- simple paraphrases of already generated questions

Prefer:
- new combinations of constraints
- new component-sensitive reasoning patterns
- schema-faithful variety over superficial wording changes

Return only these fields for each item:
- `question`
- `gold_sparql`
- `family`
- `answer_type`

Do not include any other metadata fields.

`answer_type` must be one of:
- `resource`
- `string`
- `number`
- `date`

Do not use values such as:
- `factoid`
- `non_factoid`

Return valid JSON only.
Return a JSON object with key `"items"`.
