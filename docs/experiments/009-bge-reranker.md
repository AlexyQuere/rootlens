# Experiment 009 — BGE Reranker

## Status

Completed on the DEV split only.

The frozen TEST split was not used.

---

# Objective

Evaluate whether a stronger reranker can exploit the ranking headroom identified in Experiment 007 without the regressions observed with `cross-encoder/ms-marco-MiniLM-L6-v2`.

The experiment compares:

1. Dense BGE retrieval;
2. Dense BGE + MiniLM reranking;
3. Dense BGE + BGE reranking.

All candidate-generation variables are held constant.

---

# Experimental Setup

```text
corpus              = Benchmark v2
documents           = 24
DEV queries         = 24
candidate_k         = 10
retrieval unit      = whole document

candidate retriever = BAAI/bge-small-en-v1.5
MiniLM reranker     = cross-encoder/ms-marco-MiniLM-L6-v2
BGE reranker        = BAAI/bge-reranker-base

reranker device     = MPS
```

The TEST split remains frozen.

---

# Motivation

Experiment 007 showed substantial reranking headroom:

```text
Dense Recall@3             = 0.7500
Dense Recall@10            = 0.9236
Oracle Recall@3(top10)     = 0.9236

Dense nDCG@3               = 0.8317
Oracle nDCG@3(top10)       = 0.9877
```

Experiment 008 then showed that the MiniLM reranker failed to exploit this opportunity.

Experiment 009 tests whether the failure was specific to MiniLM or whether reranking is currently a poor architectural trade-off for RootLens.

---

# Smoke Test

`BAAI/bge-reranker-base` was first validated independently.

Query:

```text
Which service calculates delivery cost before the customer is charged?
```

Scores:

```text
ShippingService  2.825774
PaymentService   0.098325
Frontend        -5.996853
```

Ranking:

```text
1. ShippingService
2. PaymentService
3. Frontend
```

The expected Shipping document ranked first and all scores were finite.

The benchmark was therefore allowed to proceed.

---

# Aggregate Results

| Metric | Dense BGE | Dense + MiniLM | Dense + BGE Reranker |
|---|---:|---:|---:|
| Precision@1 | **0.9167** | **0.9167** | 0.7500 |
| Recall@1 | **0.3507** | 0.3438 | 0.2743 |
| Recall@3 | **0.7500** | 0.6562 | 0.6840 |
| Recall@5 | **0.8299** | 0.7674 | 0.8021 |
| MRR@3 | **0.9583** | 0.9514 | 0.8681 |
| nDCG@3 | **0.8317** | 0.7725 | 0.7388 |
| nDCG@5 | **0.8500** | 0.8162 | 0.7744 |

Dense BGE remains the strongest overall system.

The BGE reranker does not improve any aggregate metric.

---

# Delta — MiniLM vs Dense

```text
Precision@1: +0.0000
Recall@1:    -0.0069
Recall@3:    -0.0938
Recall@5:    -0.0625
MRR@3:       -0.0069
nDCG@3:      -0.0592
nDCG@5:      -0.0338
```

MiniLM already degraded aggregate retrieval quality.

---

# Delta — BGE Reranker vs Dense

```text
Precision@1: -0.1667
Recall@1:    -0.0764
Recall@3:    -0.0660
Recall@5:    -0.0278
MRR@3:       -0.0903
nDCG@3:      -0.0929
nDCG@5:      -0.0756
```

The stronger BGE reranker also fails to outperform Dense BGE.

---

# Latency

Measured local latency:

## Dense BGE

```text
mean   = 9.87 ms
median = 9.49 ms
p95    = 11.56 ms
```

## Dense + MiniLM

```text
mean   = 57.03 ms
median = 48.39 ms
p95    = 55.91 ms
```

## Dense + BGE Reranker

```text
mean   = 228.96 ms
median = 204.83 ms
p95    = 254.82 ms
```

The BGE reranker is approximately 23 times slower than the Dense-only retrieval path in this local benchmark.

No aggregate retrieval-quality gain compensates for this additional cost.

---

# Category-Level Analysis

## Architecture

Dense:

```text
Precision@1 = 0.7500
Recall@3    = 0.7500
Recall@5    = 1.0000
nDCG@3      = 0.8414
```

BGE reranker:

```text
Precision@1 = 0.7500
Recall@3    = 0.7083
Recall@5    = 0.7917
nDCG@3      = 0.7854
```

Regression.

---

## Exact Identifiers

Dense:

```text
Precision@1 = 1.0000
Recall@3    = 0.9167
Recall@5    = 0.9167
nDCG@3      = 0.9607
```

BGE reranker:

```text
Precision@1 = 0.7500
Recall@3    = 0.7917
Recall@5    = 0.9167
nDCG@3      = 0.7823
```

Large regression.

---

## Hard Negatives

Dense:

```text
Precision@1 = 1.0000
Recall@3    = 0.7500
Recall@5    = 0.7500
nDCG@3      = 0.8951
```

BGE reranker:

```text
Precision@1 = 1.0000
Recall@3    = 0.7500
Recall@5    = 0.7500
nDCG@3      = 0.9131
```

Small graded-ranking improvement.

---

## Multi-Document Queries

Dense:

```text
Precision@1 = 0.6667
Recall@3    = 0.5000
Recall@5    = 0.5833
nDCG@3      = 0.7885
```

BGE reranker:

```text
Precision@1 = 0.6667
Recall@3    = 0.4167
Recall@5    = 0.5833
nDCG@3      = 0.5079
```

Large regression.

This category is particularly important for RootLens because incident investigation often requires complementary evidence from multiple sources.

---

## Observability

Dense:

```text
Precision@1 = 1.0000
Recall@3    = 0.8889
Recall@5    = 1.0000
nDCG@3      = 0.6839
```

BGE reranker:

```text
Precision@1 = 1.0000
Recall@3    = 0.8889
Recall@5    = 0.8889
nDCG@3      = 0.8323
```

Strong graded-ranking improvement, but with lower Recall@5.

---

## Semantic Paraphrase

Dense:

```text
Precision@1 = 1.0000
Recall@3    = 0.6250
Recall@5    = 0.6250
nDCG@3      = 0.8203
```

BGE reranker:

```text
Precision@1 = 0.5000
Recall@3    = 0.5417
Recall@5    = 0.7500
nDCG@3      = 0.6565
```

Recall@5 improves, but top-ranked quality and Recall@3 regress substantially.

---

## Troubleshooting

Dense:

```text
Precision@1 = 1.0000
Recall@3    = 0.7917
Recall@5    = 0.8750
nDCG@3      = 0.8163
```

BGE reranker:

```text
Precision@1 = 0.7500
Recall@3    = 0.7083
Recall@5    = 0.8750
nDCG@3      = 0.7470
```

Regression.

---

# Important Query-Level Improvements

## dev-011 — Delivery Cost

Question:

```text
Which service calculates delivery cost before the customer is charged?
```

Dense:

```text
1. payment-service.md
2. shipping-service.md
3. checkout-architecture.md
```

BGE reranker:

```text
1. shipping-service.md
2. checkout-architecture.md
3. checkout-payment-flow.md
```

Results:

```text
Recall@3:
0.667 → 1.000

nDCG@3:
0.579 → 1.000
```

This is an excellent reranking result.

---

## dev-017 — Error-Rate Detection

Results:

```text
Recall@3:
0.667 → 0.667

nDCG@3:
0.605 → 0.700
```

The reranker improves graded evidence ordering.

---

## dev-018 — Distributed Request Failure

Results:

```text
Recall@3:
1.000 → 1.000

nDCG@3:
0.689 → 0.797
```

The BGE reranker improves the ordering of distributed-tracing evidence.

---

## dev-019 — Causal Error Log Evidence

Results:

```text
Recall@3:
1.000 → 1.000

nDCG@3:
0.758 → 1.000
```

The BGE reranker produces the ideal graded top-3 ordering for this query.

---

## dev-024 — Fault-Flag Guidance

Results:

```text
Recall@3:
1.000 → 1.000

nDCG@3:
0.964 → 1.000
```

Another successful graded-ranking improvement.

---

# Important Query-Level Regressions

## dev-001 — PaymentService/Charge Ownership

Results:

```text
Recall@3:
1.000 → 1.000

nDCG@3:
0.964 → 0.659
```

The relevant set is preserved, but the primary source is demoted.

---

## dev-003 — CheckoutService/PlaceOrder

Results:

```text
Recall@3:
1.000 → 0.500

nDCG@3:
1.000 → 0.826
```

The reranker introduces an unrelated metrics document into the top 3.

---

## dev-005 — Service Discovery

Results:

```text
Recall@3:
0.500 → 0.500

nDCG@3:
0.826 → 0.413
```

The primary service-discovery source is pushed down to rank 3.

---

## dev-008 — HTTP 500 Investigation

Results:

```text
Recall@3:
0.667 → 0.333

nDCG@3:
0.847 → 0.726
```

Evidence coverage is reduced.

---

## dev-009 — Order Dependencies

Dense:

```text
checkout-architecture.md
checkout-payment-flow.md
cart-service.md
```

BGE reranker:

```text
incident-response-guide.md
checkout-architecture.md
checkout-runbook.md
```

Results:

```text
Recall@3:
1.000 → 0.500

nDCG@3:
1.000 → 0.387
```

This is one of the largest regressions.

---

## dev-020 — Network vs Application-Level Payment Failure

Results:

```text
Recall@3:
0.750 → 0.500

nDCG@3:
1.000 → 0.464
```

The reranker loses important complementary service-discovery evidence.

---

## dev-021 — Error-Rate Investigation Workflow

Results:

```text
Recall@3:
0.250 → 0.250

nDCG@3:
0.458 → 0.153
```

The reranker retrieves locally related documents but produces a much worse graded evidence set.

---

# Interpretation

Experiment 007 proved that substantial ranking headroom exists in the Dense top-10 candidate set.

However, two independent rerankers have now failed to exploit this headroom reliably:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
BAAI/bge-reranker-base
```

Both models successfully fix some local ranking errors.

This demonstrates that joint query-document scoring can improve individual relevance judgments.

However, both also introduce large regressions.

A likely explanation is that RootLens retrieval is not purely a pointwise relevance-ranking problem.

Many queries require an evidence set containing complementary sources.

For example:

```text
metrics
+
traces
+
service-discovery evidence
+
runbook evidence
```

A pointwise reranker independently estimates:

```text
score(query, document)
```

but does not explicitly optimize:

```text
coverage
diversity
complementarity
```

across the selected evidence set.

This interpretation is a hypothesis derived from the observed failure pattern, not a proven causal mechanism.

---

# Architecture Decision

Do not use either tested reranker in the default RootLens retrieval pipeline.

The selected retrieval architecture remains:

```text
Query
  ↓
BAAI/bge-small-en-v1.5
  ↓
whole-document dense retrieval
  ↓
top-k evidence
```

The following approaches remain implemented as experimental baselines:

```text
TF-IDF
BM25
Hybrid RRF
Fixed-size chunking
MiniLM reranking
BGE reranking
```

The reranker abstraction and numerical validation remain useful infrastructure for future work.

---

# Stop Condition

The reranking stop condition is triggered.

Do not continue benchmarking additional reranker models.

Tested:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
BAAI/bge-reranker-base
```

Neither improves the Dense BGE baseline.

Continuing to try additional rerankers would risk model shopping and overfitting architectural decisions to the small DEV benchmark without addressing the underlying retrieval failure mode.

---

# Next Research Question

The next problem is candidate generation and query representation.

Experiment 007 identified queries where relevant documents are absent from the top-10 Dense candidate set.

The next hypothesis is:

> A single query embedding may not express every facet of a complex operational information need.

The next stage should investigate whether alternative formulations of the same query retrieve complementary evidence.

Candidate techniques include:

```text
query rewriting
multi-query retrieval
query decomposition
```

The simplest next experiment is multi-query dense retrieval.

---

# Experiment 010 Hypothesis

> Retrieving against several controlled semantic reformulations of the same query may improve candidate recall and multi-document evidence coverage without requiring a slower pointwise reranker.

Proposed architecture:

```text
Original query
      ↓
Query rewriting
      ↓
q0 = original
q1 = rewrite 1
q2 = rewrite 2
q3 = rewrite 3
      ↓
Dense retrieval per query
      ↓
Candidate union
      ↓
Rank fusion
      ↓
Final evidence ranking
```

The original query must always be retained.

Exact identifiers and error codes must be preserved.

The rewriter must not have access to benchmark qrels.

---

# Final Conclusion

`BAAI/bge-reranker-base` produces several excellent query-level fixes but substantially degrades aggregate retrieval quality.

Compared with Dense BGE:

```text
Recall@3:
0.7500 → 0.6840

nDCG@3:
0.8317 → 0.7388

Precision@1:
0.9167 → 0.7500
```

It also increases mean local retrieval latency from approximately:

```text
9.87 ms
```

to:

```text
228.96 ms
```

The additional complexity and cost are therefore not justified.

Combined with the MiniLM result from Experiment 008, this is sufficient evidence to stop reranker tuning.

RootLens now moves from:

```text
ranking optimization
```

to:

```text
candidate-generation optimization
```

The frozen TEST split remains untouched.
