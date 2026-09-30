# Experiment 008 — Cross-Encoder Reranking

## Status

Completed on the DEV split only.

The frozen TEST split was not used.

---

# Objective

Evaluate whether a cross-encoder reranker can improve the ordering of the current Dense BGE top-10 candidate set.

Experiment 007 showed substantial ranking headroom:

```text
Actual Recall@3        = 0.7500
Oracle Recall@3(top10) = 0.9236

Actual nDCG@3          = 0.8317
Oracle nDCG@3(top10)   = 0.9877
```

This justified testing a two-stage retrieval architecture:

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

The hypothesis was:

> Joint query-document scoring should improve top-ranked evidence quality when the relevant documents are already present in the dense candidate set.

---

# Models

## Candidate retriever

```text
BAAI/bge-small-en-v1.5
```

The candidate retriever uses whole-document dense retrieval.

## Reranker

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

The reranker scores each `(query, document)` pair jointly.

The raw cross-encoder output is treated as a ranking score only.

It is not interpreted as a calibrated probability or confidence value.

---

# Candidate Depth

The reranker receives:

```text
candidate_k = 10
```

This value was selected from Experiment 007 because Dense BGE achieved:

```text
Recall@10 = 0.9236
```

while still keeping the reranking candidate set small.

---

# Hardware and Numerical Validation

The first attempted run forced the cross-encoder onto CPU.

On the local Apple Silicon environment, this produced:

```text
NaN
```

for every cross-encoder score.

Because sorting non-finite values preserved an apparently plausible ordering, the invalid run initially appeared to reproduce the dense ranking exactly.

The experiment was therefore rejected and debugged before interpretation.

The reranking implementation was updated to:

- reject `NaN`, `+Inf`, and `-Inf` scores;
- make the reranker device configurable;
- run a smoke test before benchmark evaluation.

The valid experiment used:

```text
Cross-encoder device: mps
```

The smoke test returned finite scores.

This numerical guard remains part of the implementation.

---

# Benchmark

```text
split       = DEV
documents   = 24
queries     = 24
candidate_k = 10
```

The TEST split remained frozen.

---

# Aggregate Results

| Metric | Dense BGE | Dense + Cross-Encoder | Delta |
|---|---:|---:|---:|
| Precision@1 | 0.9167 | 0.9167 | +0.0000 |
| Recall@1 | **0.3507** | 0.3438 | -0.0069 |
| Recall@3 | **0.7500** | 0.6562 | -0.0938 |
| Recall@5 | **0.8299** | 0.7674 | -0.0625 |
| MRR@3 | **0.9583** | 0.9514 | -0.0069 |
| nDCG@3 | **0.8317** | 0.7725 | -0.0592 |
| nDCG@5 | **0.8500** | 0.8162 | -0.0338 |

The cross-encoder does not improve any aggregate metric.

The largest regression is:

```text
Recall@3
0.7500 → 0.6562
```

The graded ranking metric also falls materially:

```text
nDCG@3
0.8317 → 0.7725
```

---

# Latency

The reranked pipeline measured:

```text
mean   = 71.47 ms
median = 47.29 ms
p95    = 107.61 ms
```

These measurements include candidate retrieval and cross-encoder reranking.

The current script did not measure Dense-only latency in the same run, so this experiment does not claim a precise incremental reranking overhead.

A future model-comparison experiment should measure both paths under the same timing methodology.

---

# Results by Category

## Architecture

Dense:

```text
Precision@1 = 0.7500
Recall@3    = 0.7500
Recall@5    = 1.0000
nDCG@3      = 0.8414
```

Cross-encoder:

```text
Precision@1 = 1.0000
Recall@3    = 0.5417
Recall@5    = 0.7917
nDCG@3      = 0.7814
```

The reranker improves top-1 precision but substantially reduces evidence coverage.

This illustrates why Precision@1 alone is insufficient for RootLens.

---

## Exact Identifiers

Dense:

```text
Precision@1 = 1.0000
Recall@3    = 0.9167
nDCG@3      = 0.9607
```

Cross-encoder:

```text
Precision@1 = 0.7500
Recall@3    = 0.7917
nDCG@3      = 0.8410
```

The reranker degrades a category in which Dense BGE was already very strong.

---

## Hard Negatives

The two systems are identical on the measured category:

```text
Precision@1 = 1.0000
Recall@3    = 0.7500
Recall@5    = 0.7500
nDCG@3      = 0.8951
```

The reranker provides no measurable benefit here.

---

## Multi-Document Queries

Dense:

```text
Precision@1 = 0.6667
Recall@3    = 0.5000
Recall@5    = 0.5833
nDCG@3      = 0.7885
```

Cross-encoder:

```text
Precision@1 = 0.6667
Recall@3    = 0.4167
Recall@5    = 0.5833
nDCG@3      = 0.5216
```

This is the most important regression for RootLens.

The reranker substantially worsens graded top-3 ranking for queries requiring multiple complementary evidence sources.

---

## Observability

Dense:

```text
Precision@1 = 1.0000
Recall@3    = 0.8889
Recall@5    = 1.0000
nDCG@3      = 0.6839
```

Cross-encoder:

```text
Precision@1 = 1.0000
Recall@3    = 0.8889
Recall@5    = 0.8889
nDCG@3      = 0.7728
```

This is one of the categories where reranking improves top-3 ordering.

However, Recall@5 decreases.

---

## Semantic Paraphrase

Dense:

```text
Precision@1 = 1.0000
Recall@3    = 0.6250
nDCG@3      = 0.8203
```

Cross-encoder:

```text
Precision@1 = 1.0000
Recall@3    = 0.4583
nDCG@3      = 0.7390
```

The cross-encoder substantially reduces evidence recall.

---

## Troubleshooting

Dense:

```text
Precision@1 = 1.0000
Recall@3    = 0.7917
Recall@5    = 0.8750
nDCG@3      = 0.8163
```

Cross-encoder:

```text
Precision@1 = 1.0000
Recall@3    = 0.7917
Recall@5    = 0.7917
nDCG@3      = 0.8555
```

Top-3 graded ranking improves, while Recall@5 decreases.

The reranker therefore helps some precise troubleshooting questions but does not improve overall evidence coverage.

---

# Query-Level Improvements

The aggregate regression hides several genuine successes.

## dev-006 — Telemetry Correlation

```text
Recall@3:
0.667 → 0.667

nDCG@3:
0.700 → 0.847
```

The reranker moves `telemetry-correlation.md` ahead of the more general logging evidence.

This is a successful graded-ranking improvement.

---

## dev-011 — Delivery Cost

Dense top 3:

```text
1. payment-service.md
2. shipping-service.md
3. checkout-architecture.md
```

Reranked top 3:

```text
1. shipping-service.md
2. checkout-architecture.md
3. payment-service.md
```

Metrics:

```text
Recall@3:
0.667 → 0.667

nDCG@3:
0.579 → 0.879
```

This is a strong example of the intended reranking behaviour.

The cross-encoder correctly promotes the directly relevant Shipping source above semantically related Payment content.

---

## dev-013 — UNAVAILABLE with No Server Span

Dense top 3:

```text
payment-runbook.md
grpc-troubleshooting.md
latency-troubleshooting.md
```

Reranked top 3:

```text
payment-runbook.md
grpc-troubleshooting.md
service-discovery.md
```

Metrics:

```text
Recall@3:
0.667 → 1.000

nDCG@3:
0.536 → 0.815
```

This is the clearest recall improvement produced by the reranker.

---

## dev-017 — Error-Rate Detection

```text
Recall@3:
0.667 → 0.667

nDCG@3:
0.605 → 0.700
```

The reranker improves ordering by promoting `metrics-guide.md`.

---

# Query-Level Regressions

## dev-007 — RPC Failure Before Server Receipt

Dense:

```text
grpc-troubleshooting.md
service-discovery.md
timeout-and-retry-guidance.md
```

Reranked:

```text
grpc-troubleshooting.md
payment-service.md
frontend-service.md
```

Metrics:

```text
Recall@3:
0.667 → 0.333

nDCG@3:
0.907 → 0.556
```

The reranker removes a directly useful service-discovery source from the top 3.

---

## dev-012 — Successful Checkout Sequence

Dense:

```text
checkout-payment-flow.md
frontend-service.md
payment-service.md
```

Reranked:

```text
checkout-payment-flow.md
currency-service.md
payment-service.md
```

Metrics:

```text
Recall@3:
0.667 → 0.333

nDCG@3:
0.879 → 0.726
```

The reranker over-promotes a locally relevant dependency while losing broader workflow evidence.

---

## dev-021 — Investigation from Detection to Request Evidence

Dense:

```text
incident-response-guide.md
checkout-runbook.md
frontend-service.md
```

Reranked:

```text
incident-response-guide.md
payment-monitoring.md
metrics-guide.md
```

Metrics:

```text
Recall@3:
0.250 → 0.250

nDCG@3:
0.458 → 0.121
```

This is the strongest graded-ranking regression.

The reranker promotes documents related to parts of the query while losing the evidence combination preferred by the qrels.

---

# Interpretation

The cross-encoder is not universally ineffective.

It demonstrates that joint query-document interaction can correct important local ranking errors.

Examples include:

```text
dev-011
dev-013
dev-017
```

However, its aggregate behaviour is worse than Dense BGE.

A plausible explanation is objective mismatch.

`cross-encoder/ms-marco-MiniLM-L6-v2` is a general passage-ranking model.

RootLens queries often require:

- graded evidence;
- multiple complementary documents;
- operational relationships across services;
- distinction between direct evidence and supporting evidence.

A model optimized to identify one highly relevant passage can promote locally strong matches while reducing evidence-set coverage.

This explanation is a hypothesis supported by the observed pattern, not a proven causal mechanism.

---

# Decision

Do not select `cross-encoder/ms-marco-MiniLM-L6-v2` as the default RootLens reranker.

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

The cross-encoder implementation should remain in the repository because:

- the abstraction is correct;
- numerical validation is now robust;
- the experiment produced genuine query-level improvements;
- it provides a baseline for comparing a stronger reranker.

---

# Why Reranking Is Not Rejected Entirely

Experiment 007 established substantial theoretical reranking headroom:

```text
Oracle Recall@3(top10) = 0.9236
Oracle nDCG@3(top10)   = 0.9877
```

Experiment 008 only evaluates one reranker model.

Therefore the supported conclusion is:

> This MiniLM MS MARCO reranker is not suitable enough for the current RootLens benchmark.

The unsupported conclusion would be:

> Reranking cannot help RootLens.

One more deliberately selected reranker experiment is justified before abandoning the reranking stage.

---

# Next Experiment

## Experiment 009 — Stronger Reranker Baseline

Evaluate one stronger general-purpose reranker while keeping all other variables fixed:

```text
candidate retriever = BAAI/bge-small-en-v1.5
candidate_k         = 10
retrieval unit      = whole document
benchmark split     = DEV
```

A natural candidate is:

```text
BAAI/bge-reranker-base
```

The experiment should compare:

```text
Dense BGE
vs
Dense BGE + MiniLM reranker
vs
Dense BGE + BGE reranker
```

Primary metrics:

```text
Recall@3
Recall@5
nDCG@3
nDCG@5
Precision@1
MRR@3
```

Latency must be measured for both the Dense-only and reranked paths using the same timing methodology.

If the stronger reranker still fails to improve the current Dense baseline, RootLens should stop reranker tuning and move to candidate-generation strategies.

---

# Final Conclusion

Experiment 008 produces a valid negative aggregate result.

The cross-encoder:

- fixes several important query-level ranking errors;
- improves some observability and troubleshooting rankings;
- does not improve aggregate Precision@1;
- decreases Recall@3 by 0.0938;
- decreases Recall@5 by 0.0625;
- decreases nDCG@3 by 0.0592;
- decreases nDCG@5 by 0.0338.

The additional model complexity is therefore not justified as the default architecture.

One stronger reranker baseline remains justified because Experiment 007 demonstrated substantial reranking headroom.

The frozen TEST split remains untouched.
