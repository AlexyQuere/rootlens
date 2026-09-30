## RootLens is an experimental autonomous AI system for evidence-grounded root-cause analysis of distributed systems.

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
- Stop tuning an approach when experiments no longer justify its complexity.
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
- multi-query Reciprocal Rank Fusion.

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

The DEV split is used for:

- architecture selection;
- failure analysis;
- hypothesis testing.

The TEST split remains frozen.

---

# Retrieval experiments

## Experiment 001 — TF-IDF Baseline

Established the first lexical retrieval baseline and implemented:

- tokenization;
- term frequency;
- document frequency;
- inverse document frequency;
- TF-IDF vectors;
- cosine similarity.

---

## Experiment 002 — BM25 Baseline

Added:

- term-frequency saturation;
- document-length normalization;
- BM25 IDF.

On the original calibration benchmark, BM25 did not materially outperform TF-IDF.

---

## Experiment 003 — Dense Retrieval

Introduced:

```text
BAAI/bge-small-en-v1.5
```

Dense retrieval substantially improved semantic retrieval and became the strongest retrieval baseline.

---

## Experiment 004 — Hybrid BM25 + Dense RRF

Combined lexical and dense rankings using Reciprocal Rank Fusion.

The hybrid approach improved some individual rankings but did not improve evidence recall sufficiently to replace Dense retrieval.

---

## Experiment 005 — Retrieval Benchmark v2

The larger benchmark confirmed Dense BGE as the strongest overall candidate retriever.

DEV baseline:

```text
Precision@1 = 0.9167
Recall@1    = 0.3507
Recall@3    = 0.7500
Recall@5    = 0.8299
MRR@3       = 0.9583
nDCG@3      = 0.8317
nDCG@5      = 0.8500
```

---

## Experiment 006 — Chunking and Retrieval Granularity

Compared:

```text
whole document
64 words / 16 overlap
128 words / 32 overlap
```

Whole-document retrieval clearly outperformed fixed-size chunking.

The current benchmark documents are sufficiently short and focused that chunking removes useful global context.

Whole-document retrieval therefore remains the selected granularity.

---

## Experiment 007 — Candidate Recall and Reranking Readiness

Dense candidate recall was measured at increasing depths:

```text
Recall@1  = 0.3507
Recall@3  = 0.7500
Recall@5  = 0.8299
Recall@10 = 0.9236
Recall@20 = 0.9896
```

Oracle analysis showed substantial ranking headroom:

```text
Actual Recall@3        = 0.7500
Oracle Recall@3(top10) = 0.9236

Actual nDCG@3          = 0.8317
Oracle nDCG@3(top10)   = 0.9877
```

This motivated explicit reranking experiments.

---

## Experiment 008 — MiniLM Cross-Encoder Reranking

Evaluated:

```text
Dense BGE top 10
        ↓
cross-encoder/ms-marco-MiniLM-L6-v2
```

An initial CPU run on Apple Silicon produced `NaN` reranker scores.

The retrieval pipeline was hardened to reject non-finite model outputs, and the valid experiment was rerun using MPS.

Results:

```text
                       Dense       + MiniLM

Precision@1            0.9167      0.9167
Recall@3               0.7500      0.6562
Recall@5               0.8299      0.7674
nDCG@3                 0.8317      0.7725
nDCG@5                 0.8500      0.8162
```

MiniLM reranking was not selected.

---

## Experiment 009 — BGE Reranker

A stronger reranker was evaluated:

```text
BAAI/bge-reranker-base
```

Results:

```text
                       Dense       + BGE Reranker

Precision@1            0.9167      0.7500
Recall@3               0.7500      0.6840
Recall@5               0.8299      0.8021
nDCG@3                 0.8317      0.7388
nDCG@5                 0.8500      0.7744
```

Local mean latency increased approximately from:

```text
9.87 ms
```

to:

```text
228.96 ms
```

Both tested rerankers therefore degraded the Dense baseline.

The reranking stop condition was triggered.

No additional reranker model shopping is planned.

---

## Experiment 010 — Multi-Query Retrieval

The next hypothesis was that a single query embedding may fail to express every useful semantic formulation of an operational information need.

RootLens introduced a provider-independent LLM interface and used:

```text
qwen-3.6-35b-instruct
```

to generate three semantic rewrites per DEV query.

The rewrites were generated once and frozen:

```text
data/benchmark_v2/dev_rewrites_v1.json
```

The benchmark itself is therefore deterministic and makes no LLM calls.

Architecture:

```text
original query
      +
3 semantic rewrites
      ↓
Dense BGE retrieval × 4
      ↓
candidate union
      ↓
RRF
```

### Candidate-generation result

```text
Dense candidate recall:
0.9236

Multi-query union recall:
0.9896
```

Oracle ranking potential also increased:

```text
Dense oracle Recall@3:
0.9236

Union oracle Recall@3:
0.9583
```

and:

```text
Dense oracle nDCG@3:
0.9877

Union oracle nDCG@3:
1.0000
```

Average candidate-union size:

```text
13.25 documents
```

### Final RRF ranking

```text
                       Dense       Multi-query + RRF

Precision@1            0.9167      0.9167
Recall@1               0.3507      0.3472
Recall@3               0.7500      0.7326
Recall@5               0.8299      0.8194
Recall@10              0.9236      0.9340
MRR@3                  0.9583      0.9583
nDCG@3                 0.8317      0.8394
nDCG@5                 0.8500      0.8602
```

The final ranking is mixed.

Recall@3 and Recall@5 decrease slightly while graded ranking quality improves slightly.

### Candidate-failure analysis

Experiment 007 identified six queries where a relevant document was missing from the Dense top 10.

Multi-query candidate generation recovered the missing evidence for:

```text
5 / 6
```

of these cases.

However, only:

```text
1 / 5
```

recovered documents survived into the RRF top 10.

This isolates the next bottleneck:

```text
candidate generation      → strong
candidate availability    → strong
candidate fusion          → insufficient
```

### Decision

Do not replace the Dense baseline with raw Multi-Query + RRF.

Retain multi-query retrieval as a candidate-generation mechanism.

---

# Current architecture

The current default experimental baseline remains:

```text
Query
  ↓
BAAI/bge-small-en-v1.5
  ↓
whole-document dense retrieval
  ↓
top-k evidence
```

RootLens also now has an experimental high-recall candidate-generation path:

```text
Query
  ↓
LLM semantic rewrites
  ↓
Dense retrieval for original + rewrites
  ↓
candidate union
```

This candidate pool is not yet used as the default final evidence set because fusion remains unresolved.

---

# Next experiment

## Experiment 011 — Multi-Query Fusion Strategies

Experiment 010 demonstrated that candidate generation is no longer the main bottleneck.

The next experiment keeps the candidate pool fixed and compares deterministic selection strategies.

Initial methods:

```text
RRF
MaxSim
MeanSim
```

Experimental rule:

```text
same queries
same frozen rewrites
same Dense model
same candidate pool
different fusion rule only
```

This isolates evidence selection from candidate generation.

### RRF

Uses only rank positions:

```text
RRF(d) = Σ 1 / (k + rank_i(d))
```

### MaxSim

Preserves documents that are strongly supported by at least one formulation:

```text
MaxSim(d) = max_i cosine(q_i, d)
```

### MeanSim

Rewards documents that remain relevant across several formulations:

```text
MeanSim(d) = mean_i cosine(q_i, d)
```

For MaxSim and MeanSim, every document in the fixed union candidate set is explicitly scored against every expanded query. Missing top-10 membership is not treated as a zero score.

If simple deterministic fusion still fails to exploit the high-recall pool, RootLens will move to explicit coverage/diversity-aware evidence-set selection rather than trying arbitrary additional score formulas.

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
Candidate fusion / evidence selection
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

