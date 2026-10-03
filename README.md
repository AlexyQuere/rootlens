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
- Prefer evidence-backed conclusions over architectural complexity.

## Current status

### Milestone 0 — Observable System

Completed.

RootLens first established a manual root-cause-analysis workflow on the OpenTelemetry Demo before adding any AI component.

The initial calibration incident demonstrated the investigation chain:

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

This phase established a core project rule:

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

Implemented baselines include:

- TF-IDF + cosine similarity;
- BM25;
- dense retrieval with `BAAI/bge-small-en-v1.5`;
- hybrid BM25 + Dense retrieval with Reciprocal Rank Fusion;
- fixed-size chunked dense retrieval.

The current preferred candidate retriever is:

```text
Query
  ↓
BAAI/bge-small-en-v1.5
  ↓
whole-document dense retrieval
  ↓
top-k evidence candidates
```

Whole-document retrieval is currently preferred because the benchmark documents are short and focused. Fixed-size chunking degraded retrieval quality and is retained only as an experimental capability for future long documents.

## Retrieval Benchmark v2

The current retrieval benchmark contains:

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

The hybrid approach preserved strong top-ranked results but did not improve overall evidence recall enough to justify becoming the default retriever.

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

### Experiment 006 — Chunking and retrieval granularity

Compared:

```text
whole document
64 words / 16 overlap
128 words / 32 overlap
```

Whole-document retrieval remained clearly stronger.

The experiment rejected fixed-size chunking as the default for the current short-document corpus.

### Experiment 007 — Candidate recall and reranking readiness

Dense candidate recall was measured at increasing depths:

```text
Recall@1  = 0.3507
Recall@3  = 0.7500
Recall@5  = 0.8299
Recall@10 = 0.9236
Recall@20 = 0.9896
```

The top-10 candidate set contains substantial reranking headroom:

```text
Actual Recall@3        = 0.7500
Oracle Recall@3(top10) = 0.9236

Actual nDCG@3          = 0.8317
Oracle nDCG@3(top10)   = 0.9877
```

Twelve DEV queries contain relevant documents inside the top-10 candidate set that are ranked too low in the current dense ranking.

This experimentally justifies a reranking stage.

## Current retrieval architecture

The architecture currently being evaluated is:

```text
Query
  ↓
Dense BGE candidate retrieval
  ↓
Top 10 candidates
  ↓
Cross-encoder reranker
  ↓
Top 3 / Top 5 evidence
```

The following approaches remain implemented as baselines but are not currently selected as defaults:

```text
TF-IDF
BM25
Hybrid RRF
Fixed-size chunking
```

## Next experiment

### Experiment 008 — Cross-Encoder Reranking

The next experiment evaluates a cross-encoder over the top-10 Dense BGE candidates.

The objective is to determine whether joint query-document scoring improves:

- Precision@1;
- Recall@3;
- Recall@5;
- MRR@3;
- nDCG@3;
- nDCG@5.

The experiment will also measure reranking latency and compare the gain against the additional inference cost.

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
Cross-encoder reranking
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
