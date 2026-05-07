# Models and Model Selection

This section describes the language models used in this thesis and explains why they are suitable for evaluating practical Text-to-SPARQL generation over Open Research Knowledge Graph (ORKG) template data. The main experimental focus is on open-source models, because the thesis investigates how such models can be improved through prompting, PGMR-lite, fine-tuning, and ACE-style context refinement. In addition, two proprietary OpenAI models are used in clearly separated roles: GPT-5.4 as a strong closed-source reference baseline for Direct SPARQL generation, and GPT-4o-mini as an auxiliary model for LLM-based judgement.

The model selection is designed to compare different model families rather than only different parameter counts. T5-base represents a compact encoder-decoder sequence-to-sequence model. Qwen2.5-Coder-7B-Instruct represents a code-specialized instruction model, which is relevant because SPARQL is a formal query language with code-like syntax. Mistral-7B-Instruct represents a strong general-purpose 7B instruction model. Together, these models make it possible to study whether performance differences are mainly caused by architecture, model scale, instruction tuning, code-oriented pretraining, or task-specific adaptation methods.

## Overview of Model Roles

| Model | Type | Role in this thesis | Main reason for inclusion |
|---|---|---|---|
| T5-base | Open-source encoder-decoder model | Small sequence-to-sequence baseline; full fine-tuning | Tests whether a compact text-to-text model can learn ORKG Text-to-SPARQL from supervised data. |
| Qwen2.5-Coder-7B-Instruct | Open-source decoder-only instruction model | Code-specialized 7B model; QLoRA fine-tuning | Tests whether code-oriented pretraining helps with SPARQL as a formal query language. |
| Mistral-7B-Instruct | Open-source decoder-only instruction model | General-purpose 7B instruction baseline; QLoRA fine-tuning | Tests whether a general instruction model can compete without being specifically code-specialized. |
| GPT-5.4 | Proprietary OpenAI model | Closed-source Direct SPARQL reference baseline | Provides a strong reference point for what a highly capable proprietary model can achieve. |
| GPT-4o-mini | Proprietary OpenAI model | Auxiliary LLM judge | Supports qualitative and semantic judgement where exact or execution-based metrics are insufficient. |

## T5-base

T5-base is included as the smallest and most controlled model in the comparison. T5, the “Text-to-Text Transfer Transformer”, was introduced by Raffel et al. as a unified framework that converts different NLP tasks into a text-to-text format [1]. This formulation is conceptually well aligned with Text-to-SPARQL, since the task can be represented as a transformation from a natural-language question to a textual SPARQL query. Unlike decoder-only instruction models, T5 uses an encoder-decoder architecture, which is a classical setup for sequence-to-sequence generation tasks.

In this thesis, T5-base is used as a lightweight sequence-to-sequence baseline. This is important because the thesis is not only interested in the strongest possible model, but also in the practical question of whether smaller models can be adapted to ORKG-specific query generation. T5-base can be fully fine-tuned more easily than 7B-scale causal language models. It therefore provides a useful baseline for supervised adaptation and for testing compact representations such as PGMR-lite.

The inclusion of T5-base is additionally motivated by prior work on scientific Natural-Language-to-SPARQL translation. Meloni et al. evaluate language models on scientific question answering via SPARQL generation and report that fine-tuning can make smaller models competitive in this task setting [2]. Their study explicitly discusses T5 as part of the model comparison and observes that some smaller models can achieve strong results after fine-tuning. This is directly relevant for the present thesis because the ORKG template setting also provides paired natural-language questions and gold SPARQL queries. T5-base is therefore not only a weak lower baseline, but a meaningful test of whether supervised sequence-to-sequence learning is sufficient for a constrained ORKG template task.

At the same time, T5-base has important limitations in this thesis context. It is not an instruction-tuned chat model and is less suitable for long prompts that contain extensive template descriptions, examples, and schema explanations. In addition, prior scientific Text-to-SPARQL work reports that T5 can struggle with understanding the underlying ontological schema [2]. For ORKG Text-to-SPARQL, this limitation is critical because a query may be syntactically valid but still semantically wrong if it uses incorrect classes, properties, or projections. This motivates the use of compact prompts, PGMR-lite placeholders, and ORKG memory-based restoration.

## Qwen2.5-Coder-7B-Instruct

Qwen2.5-Coder-7B-Instruct is included as the code-specialized open-source model in this thesis. Qwen2.5-Coder is a code-specific model series built on Qwen2.5. The technical report describes the series as being designed for code generation, code completion, code reasoning, and code repair, while also retaining general and mathematical capabilities [3]. The Hugging Face model card for Qwen2.5-Coder-7B-Instruct similarly presents it as part of a code-specialized model family with multiple model sizes, including the 7B variant [4].

This model is particularly relevant because SPARQL generation has properties that are close to code generation. A valid SPARQL query requires strict syntax, well-formed triple patterns, correct variable binding, consistent projection variables, and the correct use of prefixes and identifiers. Small token-level mistakes can make a query non-executable or change its meaning. A model trained or adapted for code-like structure is therefore a plausible candidate for this task.

In this thesis, Qwen2.5-Coder-7B-Instruct is expected to be especially useful for Direct SPARQL and PGMR-lite. In the Direct SPARQL setting, the model must generate a complete ORKG query with real ORKG identifiers. In the PGMR-lite setting, the model can focus more on the structural query form and produce placeholder identifiers such as `pgmr:` and `pgmrc:`, while the final grounding to ORKG identifiers is handled by the memory-based restore step. This separation is important because a code-specialized model may be strong at generating formal structure, but it cannot be assumed to know the correct ORKG schema identifiers reliably.

The main limitation of Qwen2.5-Coder-7B-Instruct in this thesis is therefore not general syntax generation, but domain-specific grounding. Code pretraining can help with structured output, but it does not automatically provide reliable knowledge of the ORKG templates, ORKG property identifiers, or the exact query patterns required for `nlp4re` and `empirical_research_practice`. For this reason, its performance must be interpreted together with schema-specific prompting, fine-tuning, PGMR restoration success, and KG-reference metrics.

## Mistral-7B-Instruct

Mistral-7B-Instruct is included as the general-purpose 7B instruction model in the comparison. The original Mistral 7B paper introduces a 7-billion-parameter language model designed for efficiency and strong performance. It highlights grouped-query attention for faster inference and sliding-window attention for efficient handling of longer sequences [5]. The Hugging Face model card for Mistral-7B-Instruct-v0.3 describes it as an instruction fine-tuned version of Mistral-7B-v0.3 [6].

In this thesis, Mistral-7B-Instruct provides an important contrast to Qwen2.5-Coder-7B-Instruct. Both models are 7B-scale instruction models, but they differ in specialization. Qwen2.5-Coder is explicitly code-oriented, whereas Mistral-7B-Instruct is a more general instruction-following model. Comparing them helps answer whether SPARQL generation benefits more from code-specialized pretraining or from general instruction-following capability.

Mistral-7B-Instruct is also relevant because prior scientific Natural-Language-to-SPARQL work found that Mistral-style models can perform strongly after optimization, while still exhibiting distinct error patterns [2]. This makes it a meaningful model for evaluating prompting, fine-tuning, and PGMR-lite in the ORKG template setting. It is not expected to know ORKG identifiers by default, but it may be capable of learning recurring query structures and following template-specific instructions.

The limitations of Mistral-7B-Instruct are similar to those of other general instruction models in this task. It may generate syntactically plausible queries that are semantically wrong, use incorrect properties, misunderstand the intended projection, or fail to preserve template-specific query patterns. Since it is not specifically trained for ORKG or SPARQL, performance depends strongly on prompting, supervised adaptation, and the availability of structured task context.

## GPT-5.4 as Proprietary Direct-SPARQL Reference Baseline

Although the main focus of this thesis is on open-source models, GPT-5.4 is used as a proprietary reference baseline. It is not part of the open-source model comparison and is not fine-tuned in this work. Instead, it serves as a strong closed-source baseline for Direct SPARQL generation. This distinction is important: GPT-5.4 is used to estimate what a highly capable proprietary model can achieve under the same task formulation, while the main research question remains how open-source models can be improved.

OpenAI describes GPT-5.4 as a frontier model for complex professional work, coding, and agentic tasks, with support for reasoning effort settings and a large context window [7]. These properties make it suitable as a strong Direct SPARQL reference model. Text-to-SPARQL requires understanding the natural-language question, following detailed template instructions, and producing a formally structured query. A strong proprietary model is therefore useful as an upper reference point for evaluating the practical gap between open-source approaches and closed-source systems.

However, GPT-5.4 must be interpreted carefully. Since it is proprietary, its architecture, training data, and detailed training procedure are not transparent. It cannot be analyzed in the same way as the open-source models. Its role is therefore not to replace the open-source comparison, but to contextualize the results. If an open-source model approaches the GPT-5.4 baseline after PGMR-lite, fine-tuning, or ACE, this indicates practical progress. If a large gap remains, the comparison helps identify where open-source models still struggle.

## GPT-4o-mini as Auxiliary LLM Judge

GPT-4o-mini is used separately as an auxiliary LLM judge. It is not one of the main Text-to-SPARQL generation models and is not part of the open-source model comparison. Instead, it supports qualitative and semantic analysis in cases where exact string-based metrics or execution-based metrics do not fully capture partial correctness.

OpenAI introduced GPT-4o-mini as a smaller and more cost-efficient model intended to make high-volume model use more affordable while still supporting strong general language capabilities [8]. The OpenAI model documentation describes GPT-4o-mini as a fast and affordable small model for focused tasks, with support for structured outputs [9]. This makes it practical for repeated judgement calls over many generated queries or error cases.

The use of an LLM judge is treated as complementary rather than primary evidence. In this thesis, execution-based metrics, answer matching, and KG-reference metrics remain the main evaluation signals. LLM judgement is useful for diagnosing semantic similarity, partial correctness, or failure cases that are difficult to capture through exact matching alone. Nevertheless, LLM-based judgement can introduce model-dependent bias and should not be interpreted as an objective replacement for executable evaluation. It is therefore used as an additional analysis layer.

## Fine-Tuning Strategy and Model Choice

The model selection also determines the fine-tuning strategy. T5-base can be fine-tuned as a full encoder-decoder sequence-to-sequence model. This is feasible because it is much smaller than the 7B-scale models and because the task can be directly represented as input text to output query.

For Qwen2.5-Coder-7B-Instruct and Mistral-7B-Instruct, full fine-tuning is less practical due to their size. This motivates parameter-efficient fine-tuning. LoRA, introduced by Hu et al., freezes the pretrained model weights and injects trainable low-rank matrices into the Transformer layers, substantially reducing the number of trainable parameters [10]. QLoRA extends this idea by backpropagating through a frozen 4-bit quantized language model into LoRA adapters, reducing memory requirements while preserving strong fine-tuning performance [11]. In this thesis, this distinction justifies full fine-tuning for T5-base and QLoRA-style adaptation for the 7B models.

This setup also supports a fairer practical comparison. The goal is not to train all models in exactly the same technical way, but to apply realistic adaptation methods for each model class. A compact encoder-decoder model can be fully fine-tuned, while larger causal language models are adapted with parameter-efficient methods that are feasible under realistic hardware constraints.

## Relation to PGMR-lite

The limitations of all selected models motivate PGMR-lite. Direct SPARQL generation requires the model to produce both the query structure and the correct ORKG identifiers. This is difficult because ORKG identifiers are not semantically transparent and cannot be assumed to be reliably stored in the model’s parametric knowledge.

PGMR addresses this issue by separating query structure generation from URI grounding. Sharma et al. propose Post-Generation Memory Retrieval as a modular framework where the language model first generates an intermediate query with placeholders and a memory module later retrieves and resolves the correct KG URIs [12]. This idea is highly relevant for the present thesis, but the implementation is adapted to the ORKG template setting. In PGMR-lite, the model generates placeholder-SPARQL using `pgmr:` and `pgmrc:` namespaces, and the restore step maps these placeholders to real ORKG identifiers using the ORKG memory.

This design is especially useful for comparing the selected models. T5-base can be tested on a shorter and more regular target representation. Qwen2.5-Coder can use its structured generation capability without needing to memorize opaque ORKG IDs. Mistral-7B-Instruct can be evaluated on whether general instruction following is sufficient for placeholder-level query construction. PGMR-lite therefore makes the comparison more diagnostic: it helps distinguish structural query generation errors from identifier-grounding errors.

## Summary of Selection Rationale

Overall, the model selection follows two complementary comparison axes. The first axis compares three open-source models with different architectural and pretraining characteristics: T5-base as a compact encoder-decoder model, Qwen2.5-Coder-7B-Instruct as a code-specialized instruction model, and Mistral-7B-Instruct as a general-purpose 7B instruction model. This axis supports the main research goal of evaluating practical improvement strategies for open-source LLMs in ORKG Text-to-SPARQL.

The second axis uses proprietary OpenAI models only as reference and analysis tools. GPT-5.4 serves as a strong closed-source Direct SPARQL baseline, while GPT-4o-mini is used for LLM-based judgement as an auxiliary diagnostic method. This separation keeps the experimental design methodologically clear. The thesis does not claim that proprietary and open-source models are directly comparable under identical transparency conditions. Instead, proprietary models provide context for interpreting the practical performance of open-source systems.

This selection makes the later results more interpretable. If T5-base improves strongly after fine-tuning or PGMR-lite, this supports the usefulness of compact supervised models for constrained ORKG templates. If Qwen2.5-Coder performs well, this suggests that code-oriented pretraining is beneficial for SPARQL-like structured generation. If Mistral-7B-Instruct performs competitively, this indicates that general instruction-following capability can be sufficient when combined with strong prompting or adaptation. Finally, comparison against GPT-5.4 helps estimate how close the improved open-source models come to a strong proprietary Direct SPARQL baseline.

## References

[1] Colin Raffel, Noam Shazeer, Adam Roberts, Katherine Lee, Sharan Narang, Michael Matena, Yanqi Zhou, Wei Li, and Peter J. Liu. 2020. *Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer*. Journal of Machine Learning Research. https://arxiv.org/abs/1910.10683

[2] Antonello Meloni, Diego Reforgiato Recupero, Francesco Osborne, Angelo Salatino, Enrico Motta, Sahar Vahdati, and Jens Lehmann. 2025. *Exploring Large Language Models for Scientific Question Answering via Natural Language to SPARQL Translation*. ACM Transactions on Intelligent Systems and Technology. https://doi.org/10.1145/3757923

[3] Binyuan Hui et al. 2024. *Qwen2.5-Coder Technical Report*. arXiv. https://arxiv.org/abs/2409.12186

[4] Qwen Team. *Qwen2.5-Coder-7B-Instruct Model Card*. Hugging Face. https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct

[5] Albert Q. Jiang et al. 2023. *Mistral 7B*. arXiv. https://arxiv.org/abs/2310.06825

[6] Mistral AI. *Mistral-7B-Instruct-v0.3 Model Card*. Hugging Face. https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3

[7] OpenAI. *GPT-5.4 Model Documentation*. OpenAI API Documentation. https://developers.openai.com/api/docs/models/gpt-5.4

[8] OpenAI. 2024. *GPT-4o mini: advancing cost-efficient intelligence*. https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/

[9] OpenAI. *GPT-4o mini Model Documentation*. OpenAI API Documentation. https://developers.openai.com/api/docs/models/gpt-4o-mini

[10] Edward J. Hu, Yelong Shen, Phillip Wallis, Zeyuan Allen-Zhu, Yuanzhi Li, Shean Wang, Lu Wang, and Weizhu Chen. 2021. *LoRA: Low-Rank Adaptation of Large Language Models*. arXiv. https://arxiv.org/abs/2106.09685

[11] Tim Dettmers, Artidoro Pagnoni, Ari Holtzman, and Luke Zettlemoyer. 2023. *QLoRA: Efficient Finetuning of Quantized LLMs*. arXiv. https://arxiv.org/abs/2305.14314

[12] Aditya Sharma, Christopher J. Pal, and Amal Zouaq. 2026. *Reducing Hallucinations in Language Model-based SPARQL Query Generation Using Post-Generation Memory Retrieval*. Findings of the Association for Computational Linguistics: EACL 2026.

