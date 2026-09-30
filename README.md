# RootLens

RootLens is an experimental autonomous AI system for evidence-grounded root-cause analysis of distributed systems.

## Core principle

```text
claim → evidence → source
```

## Current status

### Milestone 0 — Observability Foundations
Completed.

### Milestone 1 — Retrieval Foundations
Completed through Experiment 013.

Implemented and evaluated:
- TF-IDF
- BM25
- Dense BGE retrieval
- hybrid RRF
- chunking
- candidate-depth analysis
- MiniLM reranking
- BGE reranking
- semantic query rewriting
- multi-query candidate generation
- scalar fusion
- MMR
- greedy query coverage
- adaptive query decomposition
- equal-budget query-representation comparison

The next milestone is Basic Evidence-Grounded RAG.

## Retrieval Benchmark v2

```text
24 knowledge documents
24 DEV queries
16 frozen TEST queries
```

Relevance grades:

```text
2 = primary / directly relevant
1 = supporting evidence
0 = irrelevant
```

The TEST split remains frozen.

## Dense baseline

`BAAI/bge-small-en-v1.5` with whole-document retrieval:

```text
Precision@1 = 0.9167
Recall@1    = 0.3507
Recall@3    = 0.7500
Recall@5    = 0.8299
Recall@10   = 0.9236
MRR@3       = 0.9583
nDCG@3      = 0.8317
nDCG@5      = 0.8500
```

## Semantic Multi-Query Retrieval

Full semantic multi-query remains the strongest recall-oriented candidate-generation method:

```text
Candidate Recall = 0.9896
Oracle Recall@3  = 0.9583
Oracle nDCG@3    = 1.0000
Mean union size  = 13.25
Queries/query    = 4.00
```

## Experiment 013 — Query Decomposition

Equal-budget candidate generation:

```text
                   Recall   Oracle R@3   Oracle nDCG@3   Union   Queries
Dense              0.9236     0.9236        0.9877       10.00    1.00
SemanticMatched    0.9444     0.9236        0.9877       11.75    2.21
Semantic           0.9896     0.9583        1.0000       13.25    4.00
Decomposition      0.9340     0.9236        0.9877       11.50    2.21
```

Controlled query-space diversity:

```text
SemanticMatched mean cosine = 0.8947
Decomposition mean cosine   = 0.9153
```

Known Dense candidate failures recovered:

```text
SemanticMatched  2/6
Semantic         5/6
Decomposition    1/6
```

Decision:

```text
reject query decomposition as the default retrieval strategy
```

Keep Dense as the simplest default baseline and Semantic multi-query as an optional high-recall path.

## Current retrieval architecture

Default:

```text
Question
  ↓
BAAI/bge-small-en-v1.5
  ↓
whole-document Dense retrieval
  ↓
top-k evidence
```

Optional high-recall path:

```text
Question
  ↓
semantic rewrites
  ↓
Dense retrieval per formulation
  ↓
candidate union
```

## Known limitation

Persistent failure:

```text
dev-021
How should I investigate a sudden checkout error-rate increase
from detection to request-level evidence?
```

Neither semantic rewriting nor decomposition recovers:

```text
distributed-tracing-guide.md
```

This remains a benchmark limitation rather than a target for qrel-driven prompt tuning.

## Next Milestone — Basic Evidence-Grounded RAG

Experiment 014:

```text
question
→ retriever
→ evidence context
→ LLM
→ grounded answer
→ source citations
```

Initial baseline:

```text
Dense BGE whole-document retrieval
```

Optional comparison:

```text
Semantic multi-query high-recall retrieval
```

Answer-level evaluation should measure:
- correctness;
- evidence support;
- citation correctness;
- citation completeness;
- unsupported claims;
- abstention;
- sensitivity to missing evidence.

No agent yet.

## Roadmap

```text
Observability foundations              ✓
Information Retrieval foundations      ✓
Dense benchmark                        ✓
Chunking analysis                      ✓
Candidate-depth analysis               ✓
Learned reranking                      ✓
Semantic multi-query retrieval         ✓
Scalar fusion                          ✓
Set-aware evidence selection           ✓
Query decomposition                    ✓
        ↓
Basic evidence-grounded RAG            NEXT
        ↓
RAG evaluation
        ↓
Deterministic metrics/logs/traces tools
        ↓
Single investigation agent
        ↓
Agentic RAG
        ↓
Hypothesis / evidence engine
        ↓
Multi-agent evaluation
        ↓
Time-series / graph / code / Git tools
        ↓
Productization and UI
```

## Current architectural decision

Retrieval foundations are sufficient to begin RAG.

Use Dense BGE as the minimal baseline.

Retain Semantic multi-query as the high-recall comparison.

Do not continue tuning decomposition, fusion, MMR, or reranker models on DEV before measuring end-to-end answer quality.
