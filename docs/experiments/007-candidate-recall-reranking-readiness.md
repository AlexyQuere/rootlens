# Experiment 007 — Candidate Recall and Reranking Readiness

## Status

Completed on the DEV split only.

The frozen TEST split was not used.

---

# Objective

Determine whether the remaining retrieval failures are primarily caused by:

1. candidate generation failure — relevant documents are not retrieved deeply enough; or
2. ranking failure — relevant documents are present in the candidate set but ranked too low.

This distinction determines whether the next justified technique should be reranking or improved candidate generation.

The experiment uses the current preferred retriever:

```text
BAAI/bge-small-en-v1.5
```

with whole-document dense retrieval.

---

# Benchmark

```text
split     = DEV
documents = 24
queries   = 24
```

The TEST split remains frozen.

---

# Candidate Recall

Dense retrieval was evaluated at increasing candidate depths.

| Candidate depth | Recall |
|---|---:|
| Recall@1 | 0.3507 |
| Recall@3 | 0.7500 |
| Recall@5 | 0.8299 |
| Recall@10 | 0.9236 |
| Recall@20 | 0.9896 |

The candidate set becomes substantially more complete as retrieval depth increases.

In particular:

```text
Recall@3  = 0.7500
Recall@10 = 0.9236
Recall@20 = 0.9896
```

This shows that many documents missing from the top 3 are still present deeper in the dense ranking.

---

# Reranking Upper Bound

The actual top-3 metrics are:

```text
Actual Recall@3 = 0.7500
Actual nDCG@3   = 0.8317
```

An oracle reranker was then simulated by assuming perfect ordering of the relevant documents already present in a candidate set.

## Top-5 Candidates

```text
Oracle Recall@3 = 0.8299
Oracle nDCG@3   = 0.9513
```

## Top-10 Candidates

```text
Oracle Recall@3 = 0.9236
Oracle nDCG@3   = 0.9877
```

## Top-20 Candidates

```text
Oracle Recall@3 = 0.9583
Oracle nDCG@3   = 1.0000
```

---

# Interpretation

The gap between actual and oracle performance is large.

For top-10 candidates:

```text
Actual Recall@3       = 0.7500
Oracle Recall@3       = 0.9236

Actual nDCG@3         = 0.8317
Oracle nDCG@3         = 0.9877
```

Therefore a substantial part of the remaining error is caused by ranking rather than candidate generation.

This provides direct experimental justification for testing a reranker.

---

# Reranking Opportunity Count

There are 12 DEV queries where reranking the existing top-10 candidate set could improve Recall@3.

These are:

```text
dev-002
dev-005
dev-006
dev-007
dev-010
dev-011
dev-012
dev-013
dev-015
dev-017
dev-021
dev-022
```

For many of these queries, the relevant documents are already available in the top-10 set but are not ranked in the top 3.

Examples:

```text
dev-002
actual Recall@3 = 0.667
oracle Recall@3 = 1.000
```

```text
dev-005
actual Recall@3 = 0.500
oracle Recall@3 = 1.000
```

```text
dev-021
actual Recall@3 = 0.250
oracle Recall@3 = 0.750
```

This is a classic reranking-ready pattern.

---

# Candidate-Generation Failures at Top 10

Six queries still have at least one relevant document missing from the top-10 dense candidate set:

```text
dev-008
dev-015
dev-020
dev-021
dev-022
dev-023
```

Detailed failures:

```text
dev-008
Recall@10 = 0.667
missing = incident-response-guide.md
```

```text
dev-015
Recall@10 = 0.750
missing = grpc-troubleshooting.md
```

```text
dev-020
Recall@10 = 0.750
missing = grpc-troubleshooting.md
```

```text
dev-021
Recall@10 = 0.750
missing = distributed-tracing-guide.md
```

```text
dev-022
Recall@10 = 0.750
missing = metrics-guide.md
```

```text
dev-023
Recall@10 = 0.500
missing = metrics-guide.md
```

These failures cannot be repaired by a reranker limited to the top-10 candidates.

They represent a separate candidate-generation problem.

---

# Category-Level Analysis

| Category | Recall@3 | Recall@10 | Oracle Recall@3 from top 10 |
|---|---:|---:|---:|
| architecture | 0.7500 | 1.0000 | 1.0000 |
| exact_identifier | 0.9167 | 1.0000 | 1.0000 |
| hard_negative | 0.7500 | 0.7500 | 0.7500 |
| multi_document | 0.5000 | 0.7500 | 0.7500 |
| observability | 0.8889 | 1.0000 | 1.0000 |
| semantic_paraphrase | 0.6250 | 0.9167 | 0.9167 |
| troubleshooting | 0.7917 | 0.9375 | 0.9375 |

---

# Architecture

The architecture and exact-identifier categories reach complete candidate recall at top 10:

```text
Recall@10 = 1.0000
```

Therefore remaining errors in these categories are primarily ranking problems.

A reranker has enough candidate coverage to potentially achieve ideal top-3 recall.

---

# Semantic Paraphrase

Semantic paraphrase improves from:

```text
Recall@3  = 0.6250
```

to:

```text
Recall@10 = 0.9167
```

This indicates that BGE usually identifies the relevant semantic documents but does not always rank them high enough.

This category is therefore also a strong reranking target.

---

# Multi-Document Queries

Multi-document retrieval remains the weakest category:

```text
Recall@3  = 0.5000
Recall@10 = 0.7500
```

Even an oracle reranker over the top-10 candidates is capped at:

```text
Oracle Recall@3 = 0.7500
```

This means multi-document retrieval has both:

- ranking failures; and
- candidate-generation failures.

Reranking alone will not solve this category completely.

---

# Hard-Negative Queries

The hard-negative category remains:

```text
Recall@3  = 0.7500
Recall@10 = 0.7500
```

Increasing candidate depth does not improve recall.

This suggests that the missing relevant evidence is not merely ranked slightly too low.

This category may eventually benefit from:

- improved query representation;
- query expansion;
- metadata;
- alternative candidate generators.

---

# Top-20 Analysis

Dense retrieval reaches:

```text
Recall@20 = 0.9896
```

on a corpus of 24 documents.

Therefore almost every relevant document is eventually found by the dense retriever.

The oracle top-3 metrics from the top-20 candidate set are:

```text
Oracle Recall@3 = 0.9583
Oracle nDCG@3   = 1.0000
```

This confirms that the dense representation has strong candidate-generation capability when allowed sufficient depth.

However, reranking 20 of 24 documents is not a realistic long-term retrieval architecture.

The important result is that top-10 already provides a strong and practically useful candidate set.

---

# Decision

The experiment supports introducing a reranking stage.

The next architecture to evaluate is:

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

The candidate depth for the first reranking baseline should be:

```text
10
```

because:

- Recall@10 is already 0.9236;
- 12 of 24 DEV queries have measurable reranking headroom;
- top-10 keeps inference cost manageable;
- it provides a clear experimental contrast with the current dense ranking.

---

# Why a Cross-Encoder

The current dense retriever is a bi-encoder.

It computes:

```text
query → embedding
document → embedding
```

independently.

Similarity is then calculated between the two vectors.

This is efficient but loses fine-grained query-document interaction.

A cross-encoder instead evaluates:

```text
[query, document]
```

jointly.

It can model:

- token-level interactions;
- negation;
- exact relation between query intent and document content;
- subtle distinctions between hard negatives.

The trade-off is computational cost.

This makes the two-stage architecture natural:

```text
fast bi-encoder
→ candidate generation

slower cross-encoder
→ reranking
```

---

# Candidate Generation Still Needs Future Work

Although reranking is justified, it will not fix every failure.

At top 10, six queries still miss at least one relevant document.

Therefore a later experiment should target candidate generation using techniques such as:

```text
query rewriting
multi-query retrieval
query decomposition
lexical+dense candidate union
```

These techniques should only be evaluated after reranking so that RootLens can isolate ranking quality from candidate-generation quality.

---

# Experimental Hypothesis for Experiment 008

> A cross-encoder reranker applied to the top-10 dense BGE candidates should improve top-3 graded ranking quality and evidence recall, especially on queries where relevant documents are already present in the candidate set.

Primary evaluation targets:

```text
Recall@3
nDCG@3
MRR@3
Precision@1
```

Special attention should be paid to:

```text
dev-002
dev-005
dev-006
dev-007
dev-010
dev-011
dev-012
dev-013
dev-015
dev-017
dev-021
dev-022
```

These are the queries with demonstrated reranking headroom.

---

# Final Conclusion

Experiment 007 demonstrates that the current Dense BGE retriever is already a strong candidate generator.

Its candidate recall increases from:

```text
Recall@3  = 0.7500
```

to:

```text
Recall@10 = 0.9236
Recall@20 = 0.9896
```

The oracle analysis shows substantial ranking headroom:

```text
Actual Recall@3        = 0.7500
Oracle Recall@3(top10) = 0.9236

Actual nDCG@3          = 0.8317
Oracle nDCG@3(top10)   = 0.9877
```

Therefore the next justified step is a cross-encoder reranking experiment.

The frozen TEST split remains untouched.
