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
- Measure improvements rather than relying on intuition.
- Keep the system provider-agnostic.
- Document important architectural decisions.
- Compare agentic approaches against simpler alternatives.
- Keep evaluation data separate from retrieval knowledge.
- Treat model scores as ranking signals unless they are explicitly calibrated.
- Fail fast on invalid numerical outputs such as `NaN` or infinity.
- Prefer evidence-backed conclusions over architectural complexity.

## Current status

### Milestone 0 — Observable System

Completed.

RootLens first established a manual root-cause-analysis workflow on the OpenTelemetry Demo before adding any AI component.

The initial calibration incident established the investigation chain:

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

This phase established the project discipline:

```text
claim → evidence → source
```

and the distinction between:

```text
observation
interpretation
hypothesis
conclusion
```

### Milestone 1 — Retrieval Foundations

In progress.

Before building RAG or an investigation agent, RootLens is implementing and evaluating retrieval from first principles.

Implemented approaches include:

- TF-IDF + cosine similarity;
- BM25;
- dense retrieval with `BAAI/bge-small-en-v1.5`;
- hybrid BM25 + Dense retrieval with Reciprocal Rank Fusion;
- fixed-size chunked dense retrieval;
- cross-encoder reranking.

The current preferred retrieval architecture remains:

```text
Query
  ↓
BAAI/bge-small-en-v1.5
  ↓
whole-document dense retrieval
  ↓
top-k evidence
```

Whole-document retrieval is currently preferred because the benchmark documents are short and focused.

Fixed-size chunking degraded retrieval quality and is retained only as an experimental capability for future long documents.

The first cross-encoder reranker also degraded aggregate retrieval quality, so reranking is not currently part of the default architecture.

## Retrieval Benchmark v2

The benchmark contains:

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

The DEV split is used for architecture selection and failure analysis.

The TEST split is frozen and is not used for tuning.

## Retrieval experiments

### Experiment 001 — TF-IDF baseline

Established the first educational lexical retrieval baseline.

### Experiment 002 — BM25 baseline

Added term-frequency saturation and document-length normalization.

On the original calibration benchmark, BM25 did not materially improve over TF-IDF.

### Experiment 003 — Dense retrieval

Introduced local dense retrieval using:

```text
BAAI/bge-small-en-v1.5
```

Dense retrieval substantially improved semantic and paraphrase matching.

### Experiment 004 — Hybrid BM25 + Dense RRF

Combined lexical and dense rankings with Reciprocal Rank Fusion.

The hybrid approach improved some top-ranked results but did not improve overall evidence recall enough to justify becoming the default retriever.

### Experiment 005 — Retrieval Benchmark v2

The larger benchmark confirmed Dense BGE as the strongest overall candidate retriever.

Dense BGE results on DEV:

```text
Precision@1 = 0.9167
Recall@3    = 0.7500
Recall@5    = 0.8299
MRR@3       = 0.9583
nDCG@3      = 0.8317
nDCG@5      = 0.8500
```

### Experiment 006 — Chunking and Retrieval Granularity

Compared:

```text
whole document
64 words / 16 overlap
128 words / 32 overlap
```

Whole-document retrieval remained clearly stronger.

The experiment rejected fixed-size chunking as the default for the current short-document corpus.

### Experiment 007 — Candidate Recall and Reranking Readiness

Dense candidate recall was measured at increasing depths:

```text
Recall@1  = 0.3507
Recall@3  = 0.7500
Recall@5  = 0.8299
Recall@10 = 0.9236
Recall@20 = 0.9896
```

The top-10 candidate set contains substantial theoretical reranking headroom:

```text
Actual Recall@3        = 0.7500
Oracle Recall@3(top10) = 0.9236

Actual nDCG@3          = 0.8317
Oracle nDCG@3(top10)   = 0.9877
```

This justified testing a reranking stage.

### Experiment 008 — Cross-Encoder Reranking

Evaluated:

```text
Dense BGE top-10 candidates
        ↓
cross-encoder/ms-marco-MiniLM-L6-v2
```

The initial CPU run on the local Apple Silicon environment produced `NaN` reranker scores.

The pipeline was hardened to reject non-finite model outputs, and the valid experiment was rerun on MPS.

Valid DEV results:

```text
                       Dense       + Cross-Encoder
Precision@1            0.9167       0.9167
Recall@3               0.7500       0.6562
Recall@5               0.8299       0.7674
MRR@3                  0.9583       0.9514
nDCG@3                 0.8317       0.7725
nDCG@5                 0.8500       0.8162
```

The reranker improved some individual queries, including service-discovery and shipping/troubleshooting ranking cases, but degraded aggregate evidence recall and graded ranking.

The MiniLM reranker is therefore retained as an experimental baseline but is not selected for the default architecture.

## Current architecture decision

Selected:

```text
Query
  ↓
Dense BGE
  ↓
whole-document retrieval
  ↓
top-k evidence
```

Implemented but not selected as defaults:

```text
TF-IDF
BM25
Hybrid RRF
Fixed-size chunking
MiniLM cross-encoder reranking
```

## Next experiment

### Experiment 009 — Stronger Reranker Baseline

Experiment 007 demonstrated that reranking headroom exists, but Experiment 008 showed that the first MiniLM MS MARCO reranker does not exploit it reliably.

The next experiment will evaluate one stronger reranker while holding the rest of the pipeline fixed.

Candidate:

```text
BAAI/bge-reranker-base
```

Experimental controls:

```text
candidate retriever = BAAI/bge-small-en-v1.5
candidate_k         = 10
retrieval unit      = whole document
split               = DEV only
```

The experiment will compare:

```text
Dense BGE
Dense BGE + MiniLM reranker
Dense BGE + BGE reranker
```

If the stronger reranker still fails to improve the Dense baseline, RootLens will stop reranker tuning and move to candidate-generation strategies such as query rewriting, multi-query retrieval, or query decomposition.

The frozen TEST split remains untouched.

## Longer-term roadmap

```text
Observability foundations
        ↓
Retrieval foundations
        ↓
Retrieval Benchmark v2
        ↓
Dense candidate retrieval
        ↓
Reranker evaluation
        ↓
Candidate-generation improvements
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
Productization and UI
```

The project follows a simple rule:

> Complexity must earn its place through measured improvements.
