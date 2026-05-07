# Direct SPARQL Generation with Empire Compass

## Motivation and Scope

This thesis investigates how open-source language models can be used and improved for Text-to-SPARQL tasks in the context of the Open Research Knowledge Graph (ORKG). The general research interest is therefore broader than a single application: it concerns the question of how open-source models can be guided to generate executable SPARQL queries for structured scientific knowledge.

However, the concrete development and evaluation in this thesis are deliberately restricted to two ORKG templates that were taken from the EmpiRE-Compass repository: the **NLP for Requirements Engineering** template (`nlp4re`) and the **Empirical Research Practice** template (`empirical_research_practice`). The source repository is available at: <https://github.com/okarras/EmpiRE-Compass>. This restriction is motivated by the availability of suitable template-specific data and by the concrete need within the EmpiRE-Compass use case.

These two templates define the experimental scope of the thesis. Consequently, the datasets, prompt variants, Direct-SPARQL experiments, PGMR-lite transformations, fine-tuning runs, and evaluations are centered on these two template families. The goal is therefore not to solve unrestricted Text-to-SPARQL over the entire ORKG. Instead, the thesis investigates, in a controlled and template-specific ORKG setting, how open-source models can be supported through prompting, intermediate representations, fine-tuning, and agentic context engineering.

At the same time, the two selected templates serve as case studies for a broader template-based methodology. If the investigated approaches lead to improvements on these two structurally different templates, this provides indications that similar methods may also be transferable to additional ORKG templates. However, such a transfer would not be automatic. New templates would require their own template-specific datasets, prompt descriptions, PGMR mappings, and potentially additional training or adaptation data. Since this thesis considers two different templates, it also becomes possible to better assess which adaptations are template-specific and which parts of the methodology appear to be more generally reusable.

Within this scope, Direct SPARQL serves as an important baseline. In this setting, the model receives a natural-language question and directly generates a SPARQL query that should be executable against the ORKG triplestore. Unlike PGMR-lite, Direct SPARQL does not introduce a placeholder layer or a deterministic identifier restoration step. The model must therefore generate the final query structure and the correct ORKG predicates, classes, and resources in one step.

## Origin of the Empire Compass Prompting Strategy

The main Direct-SPARQL prompting strategy in this thesis is based on the Empire Compass prompt structure. This prompt structure is derived from the open-source **EmpiRE-Compass** repository by Oliver Karras et al.: <https://github.com/okarras/EmpiRE-Compass>.

EmpiRE-Compass is described as a neuro-symbolic dashboard for navigating knowledge about empirical research practice in Requirements Engineering. It combines a symbolic layer based on the ORKG with a neural layer using large language models to answer predefined and custom competency questions. The repository focuses on two themes that are directly relevant to this thesis: empirical research practices in Requirements Engineering and empirical research practices in Natural Language Processing for Requirements Engineering.

This thesis does not evaluate the complete EmpiRE-Compass application. Instead, it adapts one central idea from this repository: template-specific ORKG knowledge can be transformed into a structured prompt that supports a language model in generating SPARQL. The Empire Compass prompt is therefore used as a schema-aware Direct-SPARQL prompt. It provides the model with explicit information about ORKG prefixes, contribution patterns, template-specific classes, relevant predicates, nested property structures, and general SPARQL construction rules.

## Direct SPARQL as an Experimental Setting

In the Direct-SPARQL setting, the model is expected to generate a complete SPARQL query directly from the question. The output should contain real ORKG identifiers, such as ORKG predicates and classes, rather than abstract placeholders. After standard query extraction and prefix handling, the query should be executable against the ORKG triplestore.

This makes Direct SPARQL a strict formulation of the Text-to-SPARQL task. The model must solve several subtasks simultaneously. First, it has to understand the information need expressed in the natural-language question. Second, it has to map this information need to the correct ORKG template structure. Third, it has to generate syntactically valid SPARQL with the correct predicates, classes, and variable projections.

This is especially challenging because ORKG identifiers are not semantically transparent. For example, identifiers such as `orkgp:P181003` or `orkgc:C121001` do not explain their meaning by themselves. A correct Direct-SPARQL output therefore requires both structural query-generation ability and precise grounding in the ORKG template schema.

## Prompt Generation in the Repository

In the thesis repository, Empire Compass is implemented as a family-specific prompt mode. The prompt builder distinguishes the `empire_compass` mode from other modes and requires a template family when this mode is used. Depending on the selected family, the corresponding Empire Compass profile is loaded. If the rendered prompt file is not already available, the prompt generation process can be triggered from the repository.

The prompt generation is controlled through a runner configuration. This configuration defines one profile for the `nlp4re` family and one profile for the empirical research family. Each profile specifies the template file, the ORKG template ID, the human-readable template label, the target contribution class, and the path of the generated prompt file.

For the `nlp4re` family, the profile uses the ORKG template **NLP for Requirements Engineering** with template ID `R1544125` and target contribution class `C121001`. For the `empirical_research_practice` family, the profile uses the ORKG template **Empirical Research Practice** with template ID `R186491` and target contribution class `C27001`.

Conceptually, the prompt generation process can be summarized as follows:

```text
Template mapping
→ template-specific profile
→ target contribution class
→ dynamic SPARQL prompt generator
→ rendered family-specific Empire Compass prompt
→ natural-language question inserted into the prompt
→ model generates Direct SPARQL
```

The advantage of this structure is that the long Empire Compass prompt does not have to be manually written from scratch for each template. Instead, it is generated from template-related information and enriched with general SPARQL construction rules and family-specific guidance.

## Structure of the Generated Empire Compass Prompt

The generated Empire Compass prompt consists of several components.

First, it introduces the task as ORKG SPARQL generation. The model is instructed to generate precise and executable SPARQL for the Open Research Knowledge Graph. The prompt includes the relevant prefixes and defines the basic paper-to-contribution pattern that is used to connect papers with template-specific contribution nodes.

Second, the prompt contains the target contribution class of the selected template. This is essential because both template families describe scientific contributions, but they use different ORKG classes. The correct contribution class restricts the query to the intended template family and prevents mixing information from unrelated ORKG structures.

Third, the prompt contains a template-property section. This section lists relevant properties from the ORKG template and explains how they should be used in SPARQL triple patterns. This is important because the model does not only need to know which predicate exists; it also needs to know where in the query structure the predicate should be applied.

Fourth, the prompt describes nested template structures. Many ORKG templates are not flat. Relevant information is often stored through intermediate nodes, for example through an evaluation node, dataset node, data collection node, method node, or annotation node. The Empire Compass prompt therefore includes hierarchy information and property-chain guidance so that the model can traverse the template structure correctly.

Fifth, the prompt adds family-specific guidance. The guidance differs between the `nlp4re` and `empirical_research_practice` templates because the two templates describe different kinds of scientific information. Finally, the prompt includes general SPARQL rules, such as using labels through `rdfs:label`, using case-insensitive filters where appropriate, following nested property paths, and outputting only SPARQL without additional explanation.

## Template Family: NLP4RE

For the `nlp4re` family, the generated Empire Compass prompt is based on the ORKG template **NLP for Requirements Engineering**, which was taken from the EmpiRE-Compass repository. The profile uses template ID `R1544125` and contribution class `C121001`. The central contribution pattern is therefore:

```sparql
?paper orkgp:P31 ?contribution .
?contribution a orkgc:C121001 .
```

This pattern anchors the query in the NLP4RE template family. All family-specific information is then accessed relative to the contribution node.

The NLP4RE template focuses on studies that apply Natural Language Processing to Requirements Engineering. Accordingly, the prompt includes guidance for information such as Requirements Engineering tasks, NLP tasks, datasets, evaluation metrics, validation settings, baselines, and annotation-related information. These elements are not always represented as direct properties of the contribution. Some questions require the query to traverse intermediate nodes, for example from a contribution to an evaluation node and then to an evaluation metric.

The Empire Compass prompt therefore does more than list predicates. It also explains structural relationships between template elements. This is important for Direct SPARQL because the model has to generate the final SPARQL structure itself. If the model uses the right predicate in the wrong part of the graph, the query may still be syntactically valid but semantically incorrect or return empty results.

## Template Family: Empirical Research Practice

For the `empirical_research_practice` family, the generated Empire Compass prompt is based on the ORKG template **Empirical Research Practice**, which was also taken from the EmpiRE-Compass repository. The profile uses template ID `R186491` and contribution class `C27001`. The central contribution pattern is:

```sparql
?paper orkgp:P31 ?contribution .
?contribution a orkgc:C27001 .
```

This pattern restricts the query to contributions that instantiate the empirical research practice template. The prompt then provides additional guidance for describing empirical study characteristics.

The empirical research practice template focuses on information such as research paradigms, research questions, hypotheses, data collection, data analysis, methods, method types, threats to validity, and venue information. Similar to the NLP4RE template, not all of this information is necessarily located directly at the contribution node. For example, method-related information may require traversal from the contribution to a data collection node, then to a method node, and then to a method type.

The generated prompt therefore reflects the structure of empirical research descriptions in the ORKG. It guides the model toward queries that follow the template hierarchy rather than treating the template as a flat list of predicates. This is particularly relevant because empirical research practice contains several conceptually related but structurally distinct components, such as data collection, data analysis, research methods, and validity threats.

## Use of GPT-5.4 as Proprietary Reference Model

The Empire Compass prompt is also evaluated with the proprietary reference model `gpt_5_4`. The purpose of this evaluation is to establish a strong reference point for the Direct-SPARQL prompting strategy. Since the Empire Compass prompt provides extensive template knowledge and uses real ORKG identifiers, a strong proprietary model can show how far prompt-based Direct-SPARQL generation can be pushed when the model has strong instruction-following and code-generation capabilities.

This reference condition does not replace the comparison of open-source models. Instead, it provides an upper-reference baseline for interpreting the behavior of the open-source models. If open-source models perform worse than `gpt_5_4`, this can indicate limitations in instruction following, schema grounding, or SPARQL generation. If they improve through fine-tuning, PGMR-lite, or agentic context engineering, these improvements can then be interpreted relative to a strong Direct-SPARQL reference condition.

## Empire Compass Mini

In addition to the generated Empire Compass prompts, this thesis also uses a compact variant called **Empire Compass Mini**. This variant was created manually for the experiments in this thesis. It is not generated by the Empire Compass prompt generator and should not be understood as a direct component of the original EmpiRE-Compass repository.

The purpose of Empire Compass Mini is pragmatic. The full Empire Compass prompt contains extensive template knowledge, hierarchy information, and rule descriptions. This can be helpful for stronger models, but it can be too long or too complex for smaller models such as T5. Therefore, the mini prompts retain only the most central elements: the required output format, the contribution pattern, the most important ORKG predicates, and the natural-language question placeholder.

Empire Compass Mini therefore remains a Direct-SPARQL prompt because the model still has to output real ORKG identifiers. However, it is a manually compressed prompt variant rather than the main generator-based Empire Compass method. Its role is to make Direct-SPARQL prompting testable under stricter context and model-capacity constraints.

## Distinction from PGMR-lite

Direct SPARQL differs fundamentally from PGMR-lite. In Direct SPARQL, the model must generate the final ORKG query directly. This includes the correct SPARQL structure as well as the exact ORKG predicates, classes, and resources. Errors may therefore arise from syntax mistakes, incorrect query structure, wrong projections, missing nested paths, or incorrect ORKG identifiers.

PGMR-lite reduces this burden by replacing concrete ORKG identifiers with symbolic placeholders during generation. The model generates a more abstract query form, and a deterministic memory-based restoration step maps placeholders back to real ORKG identifiers. Direct SPARQL does not use this restoration step. As a result, Direct SPARQL measures the model's ability to perform both query construction and identifier grounding in one step, while PGMR-lite separates these two responsibilities.

This distinction makes Direct SPARQL an important baseline for the thesis. It represents the strictest and most direct version of the task, whereas PGMR-lite investigates whether a structured intermediate representation can make the task more manageable for open-source models.

## Summary

The Empire Compass Direct-SPARQL setting provides a template-specific and schema-aware baseline for this thesis. It is derived from the EmpiRE-Compass repository and uses the two ORKG templates that define the experimental scope of the work: `nlp4re` and `empirical_research_practice`. The generated prompts make template knowledge explicit by combining contribution patterns, template classes, relevant predicates, nested property structures, and general SPARQL rules.

The resulting task remains demanding because the model must generate executable SPARQL with real ORKG identifiers directly. This makes Direct SPARQL a useful baseline against which the thesis can compare alternative strategies such as PGMR-lite, fine-tuning, and agentic context engineering. At the same time, the focus on two structurally different templates allows the thesis to investigate which parts of the methodology are template-specific and which parts may be reusable for additional ORKG templates with suitable adaptation.
