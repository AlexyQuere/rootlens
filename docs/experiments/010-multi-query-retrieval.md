# Experiment 010 — Multi-Query Retrieval

## Status

Completed on the DEV split only.

The frozen TEST split was not used.

---

# Objective

Evaluate whether semantic query rewriting can improve candidate generation for RootLens by retrieving complementary evidence that is missed by a single dense query embedding.

The experiment compares:

1. Dense BGE retrieval with the original query;
2. Multi-query Dense BGE retrieval using the original query plus three frozen semantic rewrites;
3. Reciprocal Rank Fusion (RRF) over the four rankings.

The central experimental question is deliberately split into two parts:

1. **Candidate generation:** do query rewrites recover additional relevant documents?
2. **Fusion:** can RRF promote those recovered documents into the final top-k ranking?

---

# Experimental Setup

```text
corpus                  = Benchmark v2
documents               = 24
DEV queries             = 24
retrieval unit          = whole document

dense retriever         = BAAI/bge-small-en-v1.5

rewrite model           = qwen-3.6-35b-instruct
prompt version          = v2
rewrites/query          = 3
original query retained = yes

candidates/query        = 10
fusion                  = Reciprocal Rank Fusion
RRF k                   = 60
```

The TEST split remained frozen.

---

# Query-Rewrite Generation

Rewrites were generated once through the configured Aristote-compatible LLM endpoint and then frozen in:

```text
data/benchmark_v2/dev_rewrites_v1.json
```

This separates probabilistic generation from deterministic retrieval evaluation.

The benchmark itself therefore does not call the LLM.

Mean rewrite-generation latency:

```text
1324.02 ms
```

Median rewrite-generation latency:

```text
1296.06 ms
```

These values are reported for completeness but are not included in retrieval latency because the rewrites are frozen for Experiment 010.

---

# Multi-Query Architecture

```text
Original query
      ↓
      ├── q0 = original query
      ├── q1 = semantic rewrite 1
      ├── q2 = semantic rewrite 2
      └── q3 = semantic rewrite 3
              ↓
      Dense BGE retrieval
              ↓
       candidate union
              ↓
             RRF
              ↓
         final ranking
```

The original query is always preserved.

This guarantees that the union candidate set cannot lose a document that was retrieved by the original Dense query.

---

# Dense BGE Baseline

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

---

# Multi-Query + RRF

```text
Precision@1 = 0.9167
Recall@1    = 0.3472
Recall@3    = 0.7326
Recall@5    = 0.8194
Recall@10   = 0.9340
MRR@3       = 0.9583
nDCG@3      = 0.8394
nDCG@5      = 0.8602
```

---

# Aggregate Delta

```text
Precision@1 = +0.0000
Recall@1    = -0.0035
Recall@3    = -0.0174
Recall@5    = -0.0104
Recall@10   = +0.0104
MRR@3       = +0.0000
nDCG@3      = +0.0076
nDCG@5      = +0.0102
```

The final RRF ranking is mixed:

- top-1 precision is unchanged;
- top-3 and top-5 recall decrease slightly;
- Recall@10 improves slightly;
- nDCG@3 and nDCG@5 improve slightly.

Therefore Multi-Query + RRF is not a clear overall replacement for the Dense baseline.

---

# Candidate-Generation Results

The candidate-generation result is much stronger than the final ranking result.

## Candidate recall

```text
Dense candidate recall      = 0.9236
Multi-query union recall    = 0.9896
Delta                       = +0.0660
```

The multi-query union recovers almost all relevant evidence available in the DEV benchmark.

## Oracle top-3 recall

```text
Dense oracle Recall@3       = 0.9236
Union oracle Recall@3       = 0.9583
Delta                       = +0.0347
```

## Oracle nDCG@3

```text
Dense oracle nDCG@3         = 0.9877
Union oracle nDCG@3         = 1.0000
Delta                       = +0.0123
```

## Candidate-pool size

```text
Average union size          = 13.25 documents
Median union size           = 13 documents
```

This is only moderately larger than the original top-10 candidate set.

---

# Key Result

Experiment 010 successfully separates candidate generation from candidate selection.

The rewrite stage works:

```text
single-query candidate recall
0.9236
        ↓
multi-query union candidate recall
0.9896
```

However, RRF does not fully exploit the improved candidate pool.

This is the central conclusion of the experiment.

---

# Results by Category

## Architecture

Dense:

```text
Recall@3  = 0.7500
Recall@10 = 1.0000
nDCG@3    = 0.8414
```

Multi-query:

```text
Recall@3  = 0.8333
Recall@10 = 1.0000
nDCG@3    = 0.8716
```

Clear improvement.

---

## Exact Identifier

Dense:

```text
Recall@3  = 0.9167
Recall@10 = 1.0000
nDCG@3    = 0.9607
```

Multi-query:

```text
Recall@3  = 0.9167
Recall@10 = 1.0000
nDCG@3    = 0.9607
```

No measurable change.

---

## Hard Negative

Dense:

```text
Recall@3  = 0.7500
Recall@10 = 0.7500
nDCG@3    = 0.8951
```

Multi-query:

```text
Recall@3  = 0.7500
Recall@10 = 1.0000
nDCG@3    = 0.8951
```

Candidate coverage improves substantially while top-3 quality remains unchanged.

---

## Multi-Document

Dense:

```text
Recall@3  = 0.5000
Recall@10 = 0.7500
nDCG@3    = 0.7885
```

Multi-query:

```text
Recall@3  = 0.4167
Recall@10 = 0.6667
nDCG@3    = 0.8469
```

This category shows the central trade-off of Experiment 010:

- graded ranking quality improves;
- evidence recall decreases.

---

## Observability

Dense:

```text
Recall@3  = 0.8889
Recall@10 = 1.0000
nDCG@3    = 0.6839
```

Multi-query:

```text
Recall@3  = 0.7222
Recall@10 = 1.0000
nDCG@3    = 0.5375
```

Clear regression.

---

## Semantic Paraphrase

Dense:

```text
Recall@3  = 0.6250
Recall@10 = 0.9167
nDCG@3    = 0.8203
```

Multi-query:

```text
Recall@3  = 0.7083
Recall@10 = 0.9167
nDCG@3    = 0.8584
```

Clear improvement.

---

## Troubleshooting

Dense:

```text
Recall@3  = 0.7917
Recall@10 = 0.9375
nDCG@3    = 0.8163
```

Multi-query:

```text
Recall@3  = 0.7083
Recall@10 = 0.9375
nDCG@3    = 0.8595
```

Graded ranking improves while evidence recall decreases.

---

# Known Candidate-Failure Analysis

Experiment 007 identified six queries where relevant evidence was missing from the Dense top-10 candidate set.

Experiment 010 directly tests whether query rewriting can recover those missing documents.

## dev-008

Missing from Dense top 10:

```text
incident-response-guide.md
```

Recovered by multi-query union:

```text
incident-response-guide.md
```

Survives RRF top 10:

```text
no
```

Final metrics:

```text
Recall@3:
0.667 → 0.667

nDCG@3:
0.847 → 0.879
```

The rewrite stage solves the candidate-generation failure, but RRF removes the recovered document from the final top 10.

---

## dev-015

Missing from Dense top 10:

```text
grpc-troubleshooting.md
```

Recovered by union:

```text
grpc-troubleshooting.md
```

Survives RRF top 10:

```text
no
```

Final metrics:

```text
Recall@3:
0.500 → 0.500

nDCG@3:
0.907 → 0.907
```

Generation succeeds but fusion loses the new evidence.

---

## dev-020

Missing from Dense top 10:

```text
grpc-troubleshooting.md
```

Recovered by union:

```text
grpc-troubleshooting.md
```

Survives RRF top 10:

```text
no
```

Final metrics:

```text
Recall@3:
0.750 → 0.500

nDCG@3:
1.000 → 0.907
```

Candidate generation improves coverage, but RRF both loses the recovered document and worsens the final ranking.

---

## dev-021

Missing from Dense top 10:

```text
distributed-tracing-guide.md
```

Recovered by union:

```text
no
```

Survives RRF top 10:

```text
no
```

Final metrics:

```text
Recall@3:
0.250 → 0.250

nDCG@3:
0.458 → 0.726
```

This is the remaining candidate-generation failure.

The semantic rewrites remain close to the original information need and do not retrieve the missing distributed-tracing evidence.

This query is a strong candidate for future query decomposition.

---

## dev-022

Missing from Dense top 10:

```text
metrics-guide.md
```

Recovered by union:

```text
metrics-guide.md
```

Survives RRF top 10:

```text
no
```

Final metrics:

```text
Recall@3:
0.500 → 0.500

nDCG@3:
0.907 → 0.907
```

Generation succeeds; fusion fails to preserve the recovered evidence.

---

## dev-023

Missing from Dense top 10:

```text
metrics-guide.md
```

Recovered by union:

```text
metrics-guide.md
```

Survives RRF top 10:

```text
yes
```

Final metrics:

```text
Recall@3:
0.500 → 0.500

nDCG@3:
0.826 → 0.826
```

This is the only known candidate-failure query where the newly recovered document survives the RRF top-10 ranking.

---

# Recovery Summary

Among the six known Dense top-10 candidate failures:

```text
5 / 6 missing relevant documents
were recovered by the multi-query union.
```

But only:

```text
1 / 5 recovered documents
survived into the RRF top 10.
```

This is strong evidence that candidate generation improved while candidate selection / fusion remains the bottleneck.

---

# Interpretation

The experiment supports the multi-query hypothesis at the candidate-generation level.

A single query embedding does not capture all relevant lexical and semantic formulations of the operational information need.

Semantic rewrites recover documents that the original query misses.

However, standard RRF treats repeated appearance across reformulations as a strong signal.

For RootLens, this can be problematic.

A complementary evidence document may appear strongly for only one rewrite while generic documents appear moderately across several rewrites.

RRF can therefore favor repeated relevance over complementary evidence coverage.

This explanation is consistent with the observed results, but the exact causal mechanism should be tested through explicit fusion-strategy experiments.

---

# Architecture Decision

Do not replace the current Dense BGE retrieval baseline with raw Multi-Query + RRF yet.

The default remains:

```text
Query
  ↓
BAAI/bge-small-en-v1.5
  ↓
whole-document dense retrieval
```

However, retain multi-query retrieval as a candidate-generation capability.

Experiment 010 establishes that multi-query candidate generation is valuable:

```text
candidate recall:
0.9236 → 0.9896
```

Therefore the next experiment should focus on selecting evidence from the improved candidate pool.

---

# Next Research Question

The next question is:

> How should RootLens select a small final evidence set from a high-recall multi-query candidate pool?

The candidate set now contains almost all relevant evidence, but RRF does not reliably preserve it.

The next experiment should compare simple fusion / selection strategies before introducing more complex query decomposition.

Candidate strategies include:

```text
RRF
MaxSim
score aggregation
coverage-aware selection
diversity-aware selection
```

The simplest next step is to compare deterministic fusion rules on the same frozen candidate pool.

---

# Experiment 011 Hypothesis

> A fusion strategy that preserves documents strongly supported by at least one semantic rewrite may exploit the high-recall multi-query candidate pool better than standard RRF.

The experimental controls should remain fixed:

```text
Dense model           = BAAI/bge-small-en-v1.5
original query        = retained
rewrites              = frozen dev_rewrites_v1.json
rewrites/query        = 3
candidates/query      = 10
benchmark             = DEV only
```

Only the fusion strategy should change.

This isolates the selection problem from candidate generation.

---

# Final Conclusion

Experiment 010 is a positive result for **candidate generation**, but not yet for the full retrieval pipeline.

The key result is:

```text
Dense candidate recall:
0.9236

Multi-query union candidate recall:
0.9896
```

The multi-query union also improves the oracle top-3 ranking ceiling:

```text
Oracle Recall@3:
0.9236 → 0.9583

Oracle nDCG@3:
0.9877 → 1.0000
```

However, the final RRF ranking does not fully exploit this improvement:

```text
Recall@3:
0.7500 → 0.7326

Recall@5:
0.8299 → 0.8194
```

while graded ranking improves slightly:

```text
nDCG@3:
0.8317 → 0.8394

nDCG@5:
0.8500 → 0.8602
```

Therefore:

```text
query rewriting works
candidate union works
RRF is currently the bottleneck
```

RootLens should now investigate candidate fusion / evidence-set selection before adding further query-generation complexity.

The frozen TEST split remains untouched.
