# Experiment 005 — Retrieval Benchmark v2 Baselines

## Status

Completed on DEV split only.

The TEST split remains frozen and has not been used for model selection.

---

# Objective

Re-evaluate the four retrieval approaches developed during the calibration phase on a larger and more challenging RootLens benchmark.

The benchmark contains:

```text
24 operational documents
24 DEV queries
16 frozen TEST queries
```

The evaluated retrievers are:

1. TF-IDF
2. BM25
3. Dense retrieval using `BAAI/bge-small-en-v1.5`
4. Hybrid BM25 + Dense retrieval using Reciprocal Rank Fusion (RRF)

The main goals are:

- determine whether conclusions from the small calibration benchmark still hold;
- measure performance across different query families;
- identify retrieval failure modes that justify the next architectural step;
- avoid choosing retrieval complexity from intuition alone.

---

# Benchmark

## Corpus

The corpus contains 24 operational documents covering:

- application architecture;
- service responsibilities;
- gRPC troubleshooting;
- service discovery;
- DNS;
- timeouts and retries;
- metrics;
- traces;
- structured logging;
- telemetry correlation;
- OpenTelemetry Collector;
- incident response;
- operational runbooks;
- hard-negative documents.

The corpus deliberately includes overlapping vocabulary.

Examples include:

```text
payment-service.md
payment-runbook.md
payment-monitoring.md
checkout-payment-flow.md
```

These documents share terms such as:

```text
PaymentService
Checkout
Charge
latency
error
```

but answer different intents.

---

# Evaluation Set

The DEV split contains 24 queries across seven categories:

```text
architecture
exact_identifier
hard_negative
multi_document
observability
semantic_paraphrase
troubleshooting
```

Relevance is graded:

```text
2 = directly relevant / primary evidence
1 = supporting evidence
0 = irrelevant
```

Binary metrics treat grades 1 and 2 as relevant.

Graded metrics preserve the distinction between direct and supporting relevance.

---

# Metrics

The experiment reports:

- Precision@1
- Recall@1
- Recall@3
- Recall@5
- MRR@3
- nDCG@3
- nDCG@5

The benchmark also reports:

- category-level metrics;
- top-ranked results that are not grade-2 direct evidence;
- queries with incomplete Recall@3.

---

# Aggregate Results

| Retriever | Precision@1 | Recall@1 | Recall@3 | Recall@5 | MRR@3 | nDCG@3 | nDCG@5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| TF-IDF | 0.6667 | 0.2465 | 0.5972 | 0.6840 | 0.7917 | 0.6649 | 0.6967 |
| BM25 | 0.7083 | 0.2569 | 0.5938 | 0.6979 | 0.8403 | 0.6521 | 0.7025 |
| Dense BGE | 0.9167 | 0.3507 | **0.7500** | **0.8299** | 0.9583 | **0.8317** | **0.8500** |
| Hybrid RRF | **0.9583** | **0.3542** | 0.7222 | 0.7604 | **0.9792** | 0.8182 | 0.8269 |

---

# Main Result

The conclusions from the small calibration benchmark broadly survive on the larger DEV benchmark:

```text
Dense retrieval
>
lexical retrieval
```

for overall retrieval quality.

However, the larger benchmark reveals an important trade-off between Dense BGE and Hybrid RRF.

Hybrid RRF is slightly stronger on:

```text
Precision@1
Recall@1
MRR@3
```

while Dense BGE is stronger on:

```text
Recall@3
Recall@5
nDCG@3
nDCG@5
```

For a future RAG system, the second group is particularly important because retrieval must provide enough relevant evidence for generation, not only place one relevant document first.

---

# TF-IDF Analysis

## Aggregate Results

```text
Precision@1 = 0.6667
Recall@1    = 0.2465
Recall@3    = 0.5972
Recall@5    = 0.6840
MRR@3       = 0.7917
nDCG@3      = 0.6649
nDCG@5      = 0.6967
```

## Category Results

| Category | Precision@1 | Recall@3 | nDCG@3 |
|---|---:|---:|---:|
| architecture | 1.0000 | 0.7500 | 0.8334 |
| exact_identifier | 0.7500 | 0.8333 | 0.7865 |
| hard_negative | 1.0000 | 0.5000 | 0.8262 |
| multi_document | 0.6667 | 0.5000 | 0.6289 |
| observability | 0.3333 | 0.7778 | 0.5799 |
| semantic_paraphrase | 0.2500 | 0.1667 | 0.2961 |
| troubleshooting | 0.7500 | 0.6250 | 0.7536 |

## Interpretation

TF-IDF performs well when the query contains explicit vocabulary that also appears in the relevant document.

It remains strong for:

- architecture;
- exact identifiers;
- some hard-negative cases.

Its clearest weakness is semantic paraphrase:

```text
Precision@1 = 0.2500
Recall@3    = 0.1667
nDCG@3      = 0.2961
```

This confirms the vocabulary-mismatch weakness observed in the calibration benchmark.

TF-IDF also struggles with questions requiring several complementary documents.

---

# BM25 Analysis

## Aggregate Results

```text
Precision@1 = 0.7083
Recall@1    = 0.2569
Recall@3    = 0.5938
Recall@5    = 0.6979
MRR@3       = 0.8403
nDCG@3      = 0.6521
nDCG@5      = 0.7025
```

## Category Results

| Category | Precision@1 | Recall@3 | nDCG@3 |
|---|---:|---:|---:|
| architecture | 1.0000 | 0.6250 | 0.7670 |
| exact_identifier | 0.7500 | 0.8333 | 0.7865 |
| hard_negative | 1.0000 | 0.5000 | 0.8262 |
| multi_document | 1.0000 | 0.4167 | 0.5619 |
| observability | 0.3333 | 0.6111 | 0.4316 |
| semantic_paraphrase | 0.2500 | 0.4583 | 0.5104 |
| troubleshooting | 0.7500 | 0.6250 | 0.6907 |

## Interpretation

BM25 improves several ranking-oriented metrics over TF-IDF:

```text
Precision@1
Recall@1
MRR@3
```

and strongly improves semantic-paraphrase Recall@3 relative to TF-IDF:

```text
TF-IDF = 0.1667
BM25   = 0.4583
```

However, this improvement does not make BM25 a semantic retriever.

BM25 remains substantially below Dense BGE overall.

BM25 also does not improve aggregate Recall@3:

```text
TF-IDF = 0.5972
BM25   = 0.5938
```

Its main value remains as a lexical baseline and as a potentially complementary signal for exact technical vocabulary.

---

# Dense BGE Analysis

## Aggregate Results

```text
Precision@1 = 0.9167
Recall@1    = 0.3507
Recall@3    = 0.7500
Recall@5    = 0.8299
MRR@3       = 0.9583
nDCG@3      = 0.8317
nDCG@5      = 0.8500
```

Dense BGE achieves the strongest:

```text
Recall@3
Recall@5
nDCG@3
nDCG@5
```

among all evaluated retrievers.

## Category Results

| Category | Precision@1 | Recall@3 | nDCG@3 |
|---|---:|---:|---:|
| architecture | 0.7500 | 0.7500 | 0.8414 |
| exact_identifier | 1.0000 | 0.9167 | 0.9607 |
| hard_negative | 1.0000 | 0.7500 | 0.8951 |
| multi_document | 0.6667 | 0.5000 | 0.7885 |
| observability | 1.0000 | 0.8889 | 0.6839 |
| semantic_paraphrase | 1.0000 | 0.6250 | 0.8203 |
| troubleshooting | 1.0000 | 0.7917 | 0.8163 |

## Interpretation

Dense retrieval provides a major improvement over both lexical baselines.

The strongest evidence appears in:

### Semantic paraphrase

```text
TF-IDF nDCG@3 = 0.2961
BM25   nDCG@3 = 0.5104
Dense  nDCG@3 = 0.8203
```

### Troubleshooting

```text
Dense Precision@1 = 1.0000
Dense Recall@3    = 0.7917
Dense nDCG@3      = 0.8163
```

### Exact identifiers

Unexpectedly, the dense retriever also performs extremely well on exact-identifier queries:

```text
Precision@1 = 1.0000
Recall@3    = 0.9167
nDCG@3      = 0.9607
```

Therefore the larger DEV benchmark does not currently show the expected lexical advantage for exact technical identifiers.

This is evidence specific to this benchmark, not a general claim that dense retrieval always dominates lexical retrieval for identifiers.

---

# Dense Failure Analysis

Dense retrieval still has important weaknesses.

## Multi-document retrieval

The weakest category is:

```text
multi_document

Precision@1 = 0.6667
Recall@3    = 0.5000
nDCG@3      = 0.7885
```

The high nDCG but low Recall@3 indicates that dense retrieval often ranks a strong primary source well but fails to collect all supporting evidence.

This is particularly important for RootLens.

Root-cause analysis often requires multiple pieces of evidence:

```text
trace evidence
+
service-discovery evidence
+
runbook evidence
+
metrics evidence
```

A RAG system may generate an incomplete explanation if retrieval returns only the strongest individual document.

## Example: dev-021

Query:

```text
How should I investigate a sudden checkout error-rate increase from
detection to request-level evidence?
```

Dense Recall@3:

```text
0.250
```

Missing:

```text
distributed-tracing-guide.md
metrics-guide.md
telemetry-correlation.md
```

This is a strong example of a query requiring a broader evidence set.

## Example: dev-015

Query:

```text
How can I distinguish PaymentService business logic failure from failure
to reach PaymentService?
```

Dense Recall@3:

```text
0.500
```

Missing:

```text
grpc-troubleshooting.md
service-discovery.md
```

The retriever identifies useful payment-related evidence but does not recover all complementary infrastructure evidence.

---

# Hybrid RRF Analysis

## Aggregate Results

```text
Precision@1 = 0.9583
Recall@1    = 0.3542
Recall@3    = 0.7222
Recall@5    = 0.7604
MRR@3       = 0.9792
nDCG@3      = 0.8182
nDCG@5      = 0.8269
```

Hybrid RRF achieves the strongest:

```text
Precision@1
Recall@1
MRR@3
```

but underperforms Dense BGE on:

```text
Recall@3
Recall@5
nDCG@3
nDCG@5
```

---

# Hybrid Category Analysis

| Category | Precision@1 | Recall@3 | nDCG@3 |
|---|---:|---:|---:|
| architecture | 1.0000 | 0.7500 | 0.8278 |
| exact_identifier | 0.7500 | 0.9167 | 0.8766 |
| hard_negative | 1.0000 | 0.7500 | 0.8951 |
| multi_document | 1.0000 | 0.5000 | **0.8873** |
| observability | 1.0000 | 0.7778 | 0.5840 |
| semantic_paraphrase | 1.0000 | 0.5417 | 0.7718 |
| troubleshooting | 1.0000 | 0.7917 | **0.8818** |

The hybrid retriever improves some ranking behaviour.

In particular:

```text
multi_document nDCG@3
Dense  = 0.7885
Hybrid = 0.8873
```

and:

```text
troubleshooting nDCG@3
Dense  = 0.8163
Hybrid = 0.8818
```

This suggests that lexical and semantic signals can be complementary for ordering strong evidence.

However, this gain comes with lower overall candidate recall.

---

# Dense vs Hybrid Trade-off

The most important comparison is:

| Metric | Dense BGE | Hybrid RRF |
|---|---:|---:|
| Precision@1 | 0.9167 | **0.9583** |
| Recall@1 | 0.3507 | **0.3542** |
| Recall@3 | **0.7500** | 0.7222 |
| Recall@5 | **0.8299** | 0.7604 |
| MRR@3 | 0.9583 | **0.9792** |
| nDCG@3 | **0.8317** | 0.8182 |
| nDCG@5 | **0.8500** | 0.8269 |

Hybrid RRF is slightly better at getting one relevant result to the very top.

Dense BGE is better at retrieving a broader and better-ordered evidence set.

For RootLens, this distinction matters.

The downstream system will eventually need context for root-cause reasoning.

Therefore:

```text
candidate evidence recall
```

and:

```text
graded ranking quality
```

are at least as important as top-1 accuracy.

---

# Important Metric Clarification

The benchmark reports two different notions of top-ranked quality.

`Precision@1` counts both relevance grades:

```text
grade 1
grade 2
```

as relevant.

The diagnostic:

```text
Top-1 direct-relevance failures
```

is stricter.

It checks whether the top result has:

```text
grade = 2
```

Therefore the following are not contradictory:

```text
Dense Precision@1 = 0.9167
```

and:

```text
8 top-1 direct-relevance failures
```

A top-ranked grade-1 supporting document counts as relevant for
Precision@1 but still appears as a direct-relevance failure.

This distinction is one reason nDCG is important in Benchmark v2.

---

# Key Query-Level Failure Patterns

## 1. Supporting document outranks the primary source

Examples include queries where Dense returns a relevant grade-1 document
rather than the grade-2 primary source.

This hurts graded ranking quality even when binary Precision@1 remains
high.

## 2. Multi-document evidence is incomplete

This is the largest architectural weakness.

Queries such as:

```text
dev-015
dev-020
dev-021
dev-022
```

require several complementary sources.

The retriever often finds the strongest source while missing some of the
supporting evidence.

## 3. Retrieval is no longer dominated by lexical vocabulary mismatch

Unlike the calibration benchmark, semantic paraphrase is no longer the
only important problem.

Dense retrieval largely solves that failure mode.

The next bottleneck is increasingly:

```text
evidence coverage
```

rather than:

```text
basic semantic matching
```

---

# Decision

## Preferred retriever

Dense BGE remains the preferred base retriever.

The main reason is not Precision@1.

The main reason is its stronger evidence coverage and graded ranking:

```text
Recall@3 = 0.7500
Recall@5 = 0.8299
nDCG@3   = 0.8317
nDCG@5   = 0.8500
```

These metrics are especially relevant for a future RAG pipeline that
needs multiple pieces of evidence.

## Hybrid RRF

Hybrid RRF remains an experimental alternative.

It improves:

```text
top-1 precision
MRR
some troubleshooting and multi-document ranking
```

but reduces:

```text
overall Recall@3
overall Recall@5
overall nDCG
```

Therefore the additional complexity is not yet justified as the default
retriever.

## Lexical methods

TF-IDF and BM25 remain useful baselines.

They should not be removed because future corpora may contain more
opaque technical identifiers, version strings, configuration keys, and
exact error messages.

---

# What the Larger Benchmark Changed

The calibration benchmark suggested:

```text
main problem
=
semantic vocabulary mismatch
```

Benchmark v2 shows a more mature picture:

```text
semantic retrieval
largely solves vocabulary mismatch
```

but:

```text
multi-document evidence coverage
remains weak
```

This changes the next research question.

The next question is no longer simply:

> Which retriever understands the query best?

It becomes:

> How should RootLens retrieve the right evidence units and assemble a
> sufficiently complete evidence set for downstream reasoning?

---

# Next Experiment

The next experiment should focus on **chunking and retrieval granularity**.

Current retrieval operates at the whole-document level.

That creates several limitations:

1. a document may contain multiple topics;
2. a small relevant passage may be diluted by unrelated text;
3. several complementary passages may exist inside different documents;
4. future larger documents will exceed the ideal semantic unit for a
   single embedding;
5. RAG generation eventually needs passages rather than entire
   documents.

The next experiment should compare:

```text
whole-document retrieval
```

against:

```text
fixed-size chunk retrieval
```

while preserving document provenance.

Candidate configurations should initially remain simple, for example:

```text
whole document
~128-token chunks
~256-token chunks
```

with controlled overlap.

The experiment should be performed on DEV only.

The frozen TEST split must remain untouched.

---

# Hypothesis for Experiment 006

> Chunk-level dense retrieval may improve evidence coverage by allowing
> semantically focused passages to rank independently, particularly for
> multi-document and observability queries.

However, chunking may also introduce new failure modes:

- context fragmentation;
- duplicate chunks;
- loss of document-level context;
- several chunks from one document crowding out other documents;
- inflated apparent recall;
- retrieval of locally similar but globally misleading passages.

Therefore chunking must be evaluated rather than assumed to be better.

---

# Final Conclusion

Retrieval Benchmark v2 successfully exposes differences that were hidden
by the small calibration benchmark.

Dense BGE remains the strongest overall retriever for RootLens on the
DEV split.

Hybrid RRF improves top-ranked precision but sacrifices evidence recall
and graded ranking quality.

The dominant remaining retrieval problem is now incomplete evidence
coverage, especially for multi-document questions.

The next justified experiment is therefore retrieval granularity and
chunking, not further tuning of BM25, RRF, or the embedding model.

The TEST split remains frozen.
