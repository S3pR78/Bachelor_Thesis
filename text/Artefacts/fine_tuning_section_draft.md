# Fine-Tuning Setup

Fine-tuning was used as a supervised adaptation step for the selected open-source models. The goal was not to teach the models general world knowledge, but to adapt them to the recurring structures of the ORKG template queries and to the output conventions required for Text-to-SPARQL generation. In particular, the experiments tested whether supervised training improves the generation of either executable Direct-SPARQL queries or PGMR-lite queries, where symbolic placeholders are later restored to ORKG identifiers. The fine-tuning setup therefore served as a methodological comparison between direct identifier generation and a more abstract, placeholder-based target representation.

Five fine-tuning runs were configured. T5-base was fine-tuned only in the PGMR-mini setting, while Qwen2.5-Coder-7B-Instruct and Mistral-7B-Instruct were each adapted in two variants: one PGMR-lite run and one Direct-SPARQL run using the Empire Compass prompt format. This resulted in one full fine-tuning run for T5-base and four QLoRA-based adapter fine-tuning runs for the 7B models.

| Model | Fine-tuning method | Target format | Prompt mode | Epochs |
|---|---:|---|---|---:|
| T5-base | Full fine-tuning | PGMR-lite | PGMR-mini | 15 |
| Qwen2.5-Coder-7B-Instruct | QLoRA | PGMR-lite | PGMR | 3 |
| Qwen2.5-Coder-7B-Instruct | QLoRA | Direct SPARQL | Empire Compass | 3 |
| Mistral-7B-Instruct | QLoRA | PGMR-lite | PGMR | 3 |
| Mistral-7B-Instruct | QLoRA | Direct SPARQL | Empire Compass | 3 |

The Direct-SPARQL runs used the paraphrase-augmented training file `code/data/dataset/final/train_with_paraphrases.json`, with `gold_sparql` as the supervised target field. The PGMR-lite runs used `code/data/dataset/pgmr/final/train_with_paraphrases.json`, with `gold_pgmr_sparql` as the target field. Validation was performed with the corresponding `validation.json` files. After paraphrase augmentation, the training set contained 1204 examples, while the validation set contained 50 examples. For the PGMR-lite runs, examples were filtered by `pgmr_status == ok`; in the inspected local PGMR files, all PGMR training and validation entries fulfilled this condition.

All fine-tuning runs used paraphrase-augmented training data. The original 602 training examples were doubled to 1204 examples by adding paraphrased versions of the natural-language questions while keeping the corresponding gold query unchanged. This design exposes the model to different surface formulations of the same underlying query intent. The motivation follows common practice in KGQA datasets such as LC-QuAD 2.0, which includes paraphrased questions together with SPARQL queries and argues that paraphrasing increases natural-language variation and can reduce overfitting to a small set of syntactic question forms. However, in this thesis, paraphrasing is understood as a way to reduce overfitting to surface-level wording; it does not guarantee broader logical generalization to unseen query structures.

The adaptation strategy differed between T5-base and the 7B decoder-only models. T5-base was fully fine-tuned because it is a smaller encoder-decoder model and naturally fits the text-to-text formulation of the task. In contrast, Qwen2.5-Coder-7B-Instruct and Mistral-7B-Instruct were adapted using QLoRA. Full fine-tuning of 7B-parameter models would have been substantially less practical under the available compute constraints, while QLoRA allows only a small fraction of parameters to be trained through LoRA adapters on top of quantized base models. In the logged QLoRA runs, the trainable parameter share was approximately 0.53% for Qwen2.5-Coder and 0.58% for Mistral.

The main hyperparameters are summarized in Table X. The configuration reflects the different model architectures and target formats used in the experiments. T5-base was trained with a full sequence-to-sequence setup, while the Qwen2.5-Coder and Mistral variants used QLoRA with smaller per-device batch sizes and gradient accumulation. The PGMR-lite runs used shorter prompt and output limits, whereas the Direct-SPARQL runs used larger limits to accommodate the longer Empire Compass prompts and longer executable SPARQL target sequences.

| Setting | T5 PGMR-mini | Qwen/Mistral PGMR QLoRA | Qwen/Mistral Empire Compass QLoRA |
|---|---:|---:|---:|
| Epochs | 15 | 3 | 3 |
| Learning rate | $5 \times 10^{-5}$ | $2 \times 10^{-4}$ | $1 \times 10^{-4}$ |
| Train batch size | 4 | 1 | 1 |
| Eval batch size | 4 | 1 | 1 |
| Gradient accumulation | 2 | 8 | 8 |
| Max input / prompt length | 768 | 2048 | 4096 |
| Max target / output length | 512 | 512 | 1024 |
| Precision | bf16 | fp16 compute for QLoRA | fp16 compute for QLoRA |

All four QLoRA runs used LoRA rank 16, alpha 32, dropout 0.05, 4-bit loading, NF4 quantization, double quantization, float16 compute dtype, and gradient checkpointing. The LoRA adapters were applied to the attention and feed-forward projection modules of the causal language models. This setup reduced the number of trainable parameters while still allowing the models to adapt to the task-specific prompt and output format.

Training was executed via Slurm. All training scripts requested one GPU, eight CPU cores, and 80 GB of memory. The T5-base run was executed on an RTX 3090 node, while the Qwen2.5-Coder and Mistral QLoRA runs were executed on H100 NVL nodes. All five runs completed successfully. This hardware information is reported only as practical context for reproducibility and for explaining the use of QLoRA; it is not treated as a scientific result of the thesis.

The recorded wall-clock durations further illustrate the practical compute requirements of the fine-tuning setup. The T5-base PGMR-mini full fine-tuning run took approximately 31 minutes on the RTX 3090 node. The QLoRA runs on H100 NVL nodes were also completed within a practical time frame: Qwen2.5-Coder PGMR took about 28 minutes, Qwen2.5-Coder with Empire Compass took about 1 hour, Mistral PGMR took about 31 minutes, and Mistral with Empire Compass took about 1 hour and 7 minutes. The longer runtime of the Empire Compass runs is consistent with their larger prompt length and longer target/output length. These durations include training-related overhead such as setup, model loading, checkpointing, and saving, and are reported as reproducibility context rather than as a performance metric.

| Run | Hardware | Approx. wall-clock duration |
|---|---|---:|
| T5-base PGMR-mini full fine-tuning | RTX 3090 | 30 min 55 sec |
| Qwen2.5-Coder PGMR QLoRA | H100 NVL | 28 min 12 sec |
| Qwen2.5-Coder Empire Compass QLoRA | H100 NVL | 1 h 00 min 10 sec |
| Mistral PGMR QLoRA | H100 NVL | 30 min 41 sec |
| Mistral Empire Compass QLoRA | H100 NVL | 1 h 07 min 04 sec |

The training logs contain both training and validation loss values. For T5-base, the validation loss decreased steadily from 0.3313 after the first epoch to 0.1042 after the fifteenth epoch. The Qwen2.5-Coder and Mistral QLoRA runs showed comparatively small validation loss values after the first epoch, with slight fluctuations across the three epochs. These loss values indicate that the models learned the supervised target format, but they are not used as the final measure of task performance. Since Text-to-SPARQL quality depends on syntactic validity, executable queries, correct identifiers or placeholders, and answer equivalence, the final assessment is performed later using execution-based and answer-based evaluation metrics.

Methodologically, the two target formats test different learning burdens. In the Direct-SPARQL setting, the model must jointly learn the SPARQL structure and the correct ORKG identifiers for predicates, classes, and resources. This makes the output directly executable, but also places the full grounding burden on the model. In the PGMR-lite setting, the model generates SPARQL with semantic placeholders instead of opaque ORKG identifiers. The identifier grounding is then handled by a deterministic restoration step. This separation makes PGMR-lite useful for testing whether open-source models benefit from a less opaque target representation. However, PGMR-lite does not remove the need for accurate query generation: the model still has to produce valid SPARQL structure, correct placeholders, consistent variable bindings, and suitable projection variables.

Several method-level limitations follow from this setup. First, the training data is limited in size compared with large-scale text-to-SQL or code generation datasets. Second, the data is template-specific and focuses on the `nlp4re` and `empirical_research_practice` families, so generalization to other ORKG templates cannot be assumed. Third, T5-base and the 7B models use different adaptation regimes, namely full fine-tuning versus QLoRA adapter tuning, which makes the comparison practically motivated but not perfectly controlled. Finally, performance may depend strongly on prompt format, target representation, and recurring template structures, and the models may still overfit to frequently repeated query patterns. These limitations are considered in the later discussion, while the present section only defines the fine-tuning methodology.

## References

Dubey, M., Banerjee, D., Abdelkawi, A., & Lehmann, J. (2019). *LC-QuAD 2.0: A Large Dataset for Complex Question Answering over Wikidata and DBpedia*. In C. Ghidini et al. (Eds.), *The Semantic Web – ISWC 2019*, LNCS 11779, 69–78. Springer. https://doi.org/10.1007/978-3-030-30796-7_5
