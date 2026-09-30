# RootLens

RootLens is an experimental autonomous AI system for evidence-grounded root-cause analysis of distributed systems.

The project is being built incrementally to study and evaluate:

- information retrieval and RAG;
- tool-using LLMs;
- agentic workflows;
- multi-agent systems;
- observability data: metrics, logs and traces;
- hypothesis-driven incident investigation;
- evaluation of AI system architectures.

## Engineering principles

- Start with the simplest working baseline.
- Understand mechanisms before abstracting them with frameworks.
- Change one architectural variable at a time.
- Measure improvements rather than relying on intuition.
- Keep the system provider-agnostic.
- Separate probabilistic generation from deterministic evaluation.
- Keep evaluation data separate from retrieval knowledge.
- Treat model scores as ranking signals unless explicitly calibrated.
- Fail fast on invalid numerical model outputs.
- Document negative experiments as well as positive ones.
- Stop tuning approaches that do not justify their complexity.
- Compare agentic approaches against simpler alternatives.
- Prefer evidence-backed conclusions over architectural complexity.

## Project objective

RootLens aims to become an autonomous incident investigator capable of combining:

- metrics;
- logs;
- distributed traces;
- technical documentation;
- runbooks;
- historical incidents;
- source code;
- Git history;
- service topology;
- time-series evidence.

The long-term system should be able to:

1. observe an incident;
2. identify missing evidence;
3. choose tools;
4. query telemetry;
5. retrieve operational knowledge;
6. generate competing hypotheses;
7. test those hypotheses against evidence;
8. reject unsupported explanations;
9. identify the best-supported root cause;
10. explain every conclusion with traceable evidence;
11. abstain when the evidence is insufficient.

The central evidence rule is:

```text
claim → evidence → source
```

---

# Current status

## Milestone 0 — Observable System

Completed.

RootLens first established a manual root-cause-analysis workflow on the OpenTelemetry Demo before adding any AI component.

The calibration incident established the investigation chain:

```text
metrics
→ detect and quantify degradation

traces
→ localize the failing dependency

logs
→ explain the failure mechanism

additional evidence
→ establish the best-supported root cause
```

This phase also established the distinction between:

```text
observation
interpretation
hypothesis
conclusion
```

---

# Milestone 1 — Retrieval Foundations

In progress.

Before introducing RAG generation or autonomous agents, RootLens is implementing and evaluating information retrieval from first principles.

Implemented approaches include:

- TF-IDF + cosine similarity;
- BM25;
- dense retrieval;
- hybrid lexical/dense retrieval with Reciprocal Rank Fusion;
- fixed-size chunking;
- MiniLM cross-encoder reranking;
- BGE reranking;
- LLM query rewriting;
- multi-query dense candidate generation;
- RRF multi-query fusion;
- MaxSim fusion;
- MeanSim fusion.

---

# Retrieval Benchmark v2

The benchmark currently contains:

```text
24 operational knowledge documents
24 DEV queries
16 frozen TEST queries
```

Query categories include:

- exact identifiers;
- semantic paraphrases;
- architecture;
- troubleshooting;
- observability;
- multi-document questions;
- hard negatives.

Relevance judgments are graded:

```text
2 = directly relevant / primary evidence
1 = supporting evidence
0 = irrelevant
```

DEV is used for architecture selection and failure analysis.

TEST remains frozen.

---

# Retrieval experiments

## Experiment 001 — TF-IDF Baseline

Established the first lexical retrieval baseline.

## Experiment 002 — BM25 Baseline

Added term-frequency saturation and document-length normalization.

BM25 did not materially outperform the original lexical baseline.

## Experiment 003 — Dense Retrieval

Introduced:

```text
BAAI/bge-small-en-v1.5
```

Dense retrieval substantially improved semantic retrieval.

## Experiment 004 — Hybrid BM25 + Dense RRF

Combined lexical and dense rankings using Reciprocal Rank Fusion.

The additional complexity did not improve evidence recall sufficiently to replace Dense retrieval.

## Experiment 005 — Retrieval Benchmark v2

Dense BGE became the primary benchmark baseline:

```text
Precision@1 = 0.9167
Recall@1    = 0.3507
Recall@3    = 0.7500
Recall@5    = 0.8299
MRR@3       = 0.9583
nDCG@3      = 0.8317
nDCG@5      = 0.8500
```

## Experiment 006 — Chunking and Retrieval Granularity

Whole-document retrieval outperformed fixed-size chunking on the current short operational documents.

## Experiment 007 — Candidate Recall and Reranking Readiness

Dense candidate-depth analysis showed:

```text
Recall@1  = 0.3507
Recall@3  = 0.7500
Recall@5  = 0.8299
Recall@10 = 0.9236
Recall@20 = 0.9896
```

Oracle analysis showed substantial ranking headroom.

## Experiment 008 — MiniLM Cross-Encoder Reranking

`cross-encoder/ms-marco-MiniLM-L6-v2` degraded aggregate retrieval quality.

An invalid Apple-Silicon CPU run also exposed the importance of rejecting non-finite model scores.

## Experiment 009 — BGE Reranker

`BAAI/bge-reranker-base` also degraded aggregate retrieval quality while substantially increasing latency.

The reranker-model stop condition was triggered.

## Experiment 010 — Multi-Query Retrieval

Three semantic rewrites were generated per DEV query with:

```text
qwen-3.6-35b-instruct
```

The rewrites were frozen in:

```text
data/benchmark_v2/dev_rewrites_v1.json
```

Multi-query candidate generation increased candidate recall:

```text
Dense candidate recall:
0.9236

Multi-query union candidate recall:
0.9896
```

Oracle ranking potential also increased:

```text
Dense oracle Recall@3:
0.9236

Union oracle Recall@3:
0.9583

Dense oracle nDCG@3:
0.9877

Union oracle nDCG@3:
1.0000
```

However, RRF preserved only one of five newly recovered relevant documents in its top 10.

Candidate generation was therefore validated, while candidate fusion became the next bottleneck.

## Experiment 011 — Multi-Query Fusion Strategies

Experiment 011 kept the high-recall candidate union fixed and compared:

```text
RRF
MaxSim
MeanSim
```

Aggregate results:

```text
                 Dense    RRF      MaxSim   MeanSim

Precision@1      0.9167   0.9167   0.9167   0.9167
Recall@3         0.7500   0.7326   0.7049   0.7257
Recall@5         0.8299   0.8194   0.8299   0.8125
Recall@10        0.9236   0.9340   0.9340   0.9340
MRR@3            0.9583   0.9583   0.9583   0.9583
nDCG@3           0.8317   0.8394   0.8177   0.8316
nDCG@5           0.8500   0.8602   0.8493   0.8455
```

RRF remained the strongest fusion rule on aggregate graded ranking, but none of the three methods improved top-3 evidence recall over Dense.

Most importantly, all three methods retained only:

```text
1 / 5
```

newly recovered relevant documents in their top 10.

This rejects the hypothesis that the Experiment 010 bottleneck is specific to RRF.

The evidence-selection problem is broader:

```text
candidate generation      → strong
candidate availability    → strong
scalar fusion             → insufficient
```

The next step is set-aware evidence selection.

---

# Current architecture

The default experimental baseline remains:

```text
Query
  ↓
BAAI/bge-small-en-v1.5
  ↓
whole-document dense retrieval
  ↓
top-k evidence
```

RootLens also retains an experimental high-recall path:

```text
Query
  ↓
LLM semantic rewrites
  ↓
Dense retrieval for original + rewrites
  ↓
candidate union
```

The union candidate pool is not yet used as the default final evidence set.

---

# Next experiment

## Experiment 012 — Set-Aware Evidence Selection

Experiment 011 shows that independent scalar scoring is not sufficient to exploit the multi-query candidate union.

The next experiment will treat the output as a set-selection problem.

Keep fixed:

```text
Dense model           = BAAI/bge-small-en-v1.5
frozen rewrites       = dev_rewrites_v1.json
rewrites/query        = 3
candidates/query      = 10
candidate union       = unchanged
benchmark             = DEV only
```

Compare:

```text
Dense baseline
RRF baseline
MMR
query-coverage selection
```

### MMR

Maximal Marginal Relevance balances relevance with non-redundancy:

```text
MMR(d | S)
=
λ * relevance(d)
-
(1 - λ) * max similarity(d, selected_document)
```

### Query-Coverage Selection

Instead of assigning one independent scalar to each document, greedily select documents that improve coverage across the expanded query representations.

The goal is to test whether a set-aware objective can preserve complementary evidence that simple RRF, MaxSim, and MeanSim discard.

If set-aware selection still cannot exploit the candidate union, the next step will be explicit query decomposition.

---

# Longer-term roadmap

```text
Observability foundations
        ↓
Information-retrieval foundations
        ↓
Dense retrieval
        ↓
Retrieval benchmark
        ↓
Chunking evaluation
        ↓
Candidate-depth analysis
        ↓
Reranking experiments
        ↓
Multi-query candidate generation
        ↓
Scalar fusion experiments
        ↓
Set-aware evidence selection
        ↓
Query decomposition
        ↓
Basic RAG
        ↓
RAG evaluation
        ↓
Deterministic observability tools
        ↓
Single investigation agent
        ↓
Agentic RAG
        ↓
Hypothesis / evidence investigation engine
        ↓
Multi-agent evaluation
        ↓
Productization
```

The project follows one central architectural rule:

> Complexity must earn its place through measured improvements.
