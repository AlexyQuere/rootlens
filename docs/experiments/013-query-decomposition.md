# Experiment 013 — Query Decomposition

## Status
Completed on the Benchmark v2 DEV split only. The frozen TEST split was not used.

## Objective
Test whether explicit query decomposition can produce a better retrieval candidate pool than semantic query rewriting.

Experiment 013 compares:
- Dense
- SemanticMatched
- Semantic
- Decomposition

`SemanticMatched` is an equal-budget control: for each query it uses the same number of retrieval queries as the decomposition method, consuming frozen semantic rewrites in their original order.

## Experimental Setup

```text
corpus                     = Benchmark v2
documents                  = 24
DEV queries                = 24
retrieval unit             = whole document
dense model                = BAAI/bge-small-en-v1.5
candidates per query       = 10
RRF k                      = 60
```

Frozen semantic rewrites:

```text
data/benchmark_v2/dev_rewrites_v1.json
```

Frozen decompositions:

```text
data/benchmark_v2/dev_decompositions_v3.json
```

Decomposition generation:

```text
maximum decompositions     = 3
total generated subqueries = 35
mean subqueries/query      = 1.46
queries with 1 subquery    = 15
queries with 2 subqueries  = 7
queries with 3 subqueries  = 2
```

## Candidate Generation Results

| Method | Candidate Recall | Oracle Recall@3 | Oracle nDCG@3 | Mean Union Size | Mean Retrieval Queries |
|---|---:|---:|---:|---:|---:|
| Dense | 0.9236 | 0.9236 | 0.9877 | 10.00 | 1.00 |
| SemanticMatched | 0.9444 | 0.9236 | 0.9877 | 11.75 | 2.21 |
| Semantic | **0.9896** | **0.9583** | **1.0000** | 13.25 | 4.00 |
| Decomposition | 0.9340 | 0.9236 | 0.9877 | 11.50 | 2.21 |

At equal retrieval budget:

```text
SemanticMatched    0.9444
Decomposition      0.9340
```

Decomposition therefore does not outperform semantic rewriting when retrieval budget is controlled.

## Query Representation Diversity

Lower cosine means greater semantic diversity.

```text
Semantic full mean pairwise cosine   = 0.8776
SemanticMatched mean pairwise cosine = 0.8947
Decomposition mean pairwise cosine   = 0.9153
```

The controlled SemanticMatched-versus-Decomposition comparison is computed over the same 19 comparable queries.

The decomposition queries are, on average, more similar in the BGE retrieval space.

## Candidate Recall by Category

| Category | Dense | SemanticMatched | Semantic | Decomposition |
|---|---:|---:|---:|---:|
| architecture | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| exact_identifier | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| hard_negative | 0.7500 | 0.7500 | **1.0000** | 0.7500 |
| multi_document | 0.7500 | **0.9167** | **0.9167** | 0.8333 |
| observability | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| semantic_paraphrase | 0.9167 | 0.9167 | **1.0000** | 0.9167 |
| troubleshooting | 0.9375 | 0.9375 | **1.0000** | 0.9375 |

## Final Ranking Diagnostic

| Metric | Dense | SemanticMatchedRRF | SemanticRRF | DecompositionRRF |
|---|---:|---:|---:|---:|
| Precision@1 | 0.9167 | **0.9583** | 0.9167 | 0.9167 |
| Recall@1 | 0.3507 | **0.3611** | 0.3472 | 0.3507 |
| Recall@3 | **0.7500** | 0.6840 | 0.7326 | 0.7188 |
| Recall@5 | 0.8299 | **0.8507** | 0.8194 | 0.8472 |
| Recall@10 | 0.9236 | **0.9340** | **0.9340** | 0.9132 |
| MRR@3 | 0.9583 | **0.9792** | 0.9583 | 0.9583 |
| nDCG@3 | 0.8317 | 0.8211 | **0.8394** | 0.8191 |
| nDCG@5 | 0.8500 | **0.8711** | 0.8602 | 0.8500 |

These results reinforce that candidate generation and final ranking are distinct problems.

## Known Candidate Failures

```text
SemanticMatched  2 / 6
Semantic         5 / 6
Decomposition    1 / 6
```

The persistent unresolved failure remains `dev-021`, where neither semantic rewriting nor decomposition recovers `distributed-tracing-guide.md`.

## Interpretation

At equal query budget:

```text
SemanticMatched  0.9444
Decomposition    0.9340
```

and query-space diversity is also worse for decomposition:

```text
SemanticMatched cosine  = 0.8947
Decomposition cosine    = 0.9153
```

The decomposition hypothesis is therefore not supported on the current DEV benchmark.

The absolute difference is small on only 24 DEV queries, so this should not be generalized beyond this experiment. But there is no evidence here that decomposition deserves to become the default retrieval strategy.

Full semantic multi-query remains the strongest recall-oriented candidate generator:

```text
Candidate Recall = 0.9896
Oracle Recall@3  = 0.9583
Oracle nDCG@3    = 1.0000
```

## Decision

Reject explicit query decomposition as the default retrieval strategy for the current RootLens benchmark.

Do not:
- create prompt v4;
- tune decompositions against qrels;
- add decomposition-specific weights;
- increase decomposition count.

Keep:
- Dense BGE as the simplest default retrieval baseline;
- semantic multi-query as an optional high-recall candidate-generation path.

Move next to answer-level RAG evaluation instead of continuing retrieval heuristic tuning.

## Next Experiment — Experiment 014: Basic Evidence-Grounded RAG

Build the smallest end-to-end RAG baseline:

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

Evaluate:
- answer correctness;
- evidence support;
- citation correctness;
- citation completeness;
- unsupported-claim rate;
- abstention when evidence is insufficient;
- sensitivity to missing evidence.

The first implementation should remain deterministic in orchestration. No agent yet.

## Final Conclusion

Experiment 013 rejects the query-decomposition hypothesis for the current RootLens retrieval stack.

The frozen TEST split remains untouched.
