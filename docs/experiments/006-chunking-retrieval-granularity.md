# Experiment 006 — Chunking and Retrieval Granularity

## Status

Completed on the DEV split only.

The frozen TEST split was not used.

---

# Objective

Evaluate whether chunk-level dense retrieval improves RootLens retrieval quality compared with whole-document dense retrieval.

The experiment tests the hypothesis:

> Smaller semantic units may allow highly relevant passages to rank more strongly than an embedding of an entire document, especially for multi-document and observability queries.

Three configurations were compared:

1. whole-document dense retrieval;
2. 64-word chunks with 16-word overlap;
3. 128-word chunks with 32-word overlap.

All configurations use the same dense encoder:

```text
BAAI/bge-small-en-v1.5
```

Chunk-level scores are aggregated back to document level using the maximum chunk score:

\[
score(D,Q)
=
\max_{c \in D}
similarity(Q,c)
\]

This keeps evaluation compatible with the existing document-level relevance judgments.

---

# Experimental Setup

## Benchmark

```text
split     = DEV
documents = 24
queries   = 24
```

The TEST split remains frozen.

## Retrieval Units

The number of indexed retrieval units was:

```text
Whole document: 24
64 / 16 chunks: 90
128 / 32 chunks: 48
```

The corpus documents are relatively short, approximately 129–218 words each.

This is important when interpreting the results: the whole documents already fit comfortably within the embedding model's useful context window.

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

The Recall@3 diagnostic was corrected to compare actual recall with the maximum mathematically achievable Recall@3 for each query.

For example, if a query has four relevant documents:

\[
\max Recall@3
=
\frac{3}{4}
=
0.75
\]

A query achieving 0.75 is therefore not marked as suboptimal.

---

# Aggregate Results

| Configuration | Precision@1 | Recall@1 | Recall@3 | Recall@5 | MRR@3 | nDCG@3 | nDCG@5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Whole document | **0.9167** | **0.3507** | **0.7500** | **0.8299** | **0.9583** | **0.8317** | **0.8500** |
| 64 words / 16 overlap | 0.8333 | 0.3194 | 0.6076 | 0.6806 | 0.8750 | 0.7314 | 0.7483 |
| 128 words / 32 overlap | 0.7917 | 0.3056 | 0.6146 | 0.7431 | 0.8889 | 0.7228 | 0.7795 |

Whole-document dense retrieval is clearly stronger overall.

Neither chunking configuration improves any aggregate evaluation metric.

---

# Whole-Document Baseline

Whole-document dense retrieval achieved:

```text
Precision@1 = 0.9167
Recall@1    = 0.3507
Recall@3    = 0.7500
Recall@5    = 0.8299
MRR@3       = 0.9583
nDCG@3      = 0.8317
nDCG@5      = 0.8500
```

This reproduces the Dense BGE baseline from Experiment 005.

The strongest category-level results include:

```text
exact_identifier:
Precision@1 = 1.0000
Recall@3    = 0.9167
nDCG@3      = 0.9607

observability:
Precision@1 = 1.0000
Recall@3    = 0.8889

troubleshooting:
Precision@1 = 1.0000
Recall@3    = 0.7917

semantic_paraphrase:
Precision@1 = 1.0000
Recall@3    = 0.6250
nDCG@3      = 0.8203
```

The main remaining weakness is still multi-document evidence coverage.

---

# 64-Word Chunks with 16-Word Overlap

## Aggregate Results

```text
Precision@1 = 0.8333
Recall@1    = 0.3194
Recall@3    = 0.6076
Recall@5    = 0.6806
MRR@3       = 0.8750
nDCG@3      = 0.7314
nDCG@5      = 0.7483
```

This configuration strongly degrades retrieval quality.

## Category Results

Notable values include:

```text
multi_document:
Precision@1 = 0.3333
Recall@3    = 0.4167
nDCG@3      = 0.4650

semantic_paraphrase:
Precision@1 = 0.7500
Recall@3    = 0.3750
nDCG@3      = 0.6149

observability:
Precision@1 = 0.6667
Recall@3    = 0.7222
nDCG@3      = 0.6141
```

These are all materially below the whole-document baseline.

## Example Failure: dev-021

For the query about investigating a checkout error-rate increase from detection to request-level evidence:

```text
Whole-document Recall@3 = 0.250
64 / 16 Recall@3        = 0.000
```

The chunked retriever misses all four judged relevant documents in the top 3:

```text
checkout-runbook.md
distributed-tracing-guide.md
metrics-guide.md
telemetry-correlation.md
```

Chunking therefore makes the multi-evidence problem worse rather than solving it.

---

# 128-Word Chunks with 32-Word Overlap

## Aggregate Results

```text
Precision@1 = 0.7917
Recall@1    = 0.3056
Recall@3    = 0.6146
Recall@5    = 0.7431
MRR@3       = 0.8889
nDCG@3      = 0.7228
nDCG@5      = 0.7795
```

The larger chunks recover some Recall@5 compared with 64/16:

```text
64 / 16  Recall@5 = 0.6806
128 / 32 Recall@5 = 0.7431
```

but remain substantially below whole-document retrieval:

```text
Whole document Recall@5 = 0.8299
```

The larger chunks therefore reduce some fragmentation but do not make chunking competitive.

---

# Why Chunking Hurt

## 1. The Documents Are Already Short

The current benchmark documents are approximately 129–218 words long.

They are already compact semantic units.

Whole-document embeddings therefore preserve useful context without suffering from severe topic dilution or model truncation.

Chunking solves a problem that the current corpus does not yet have.

---

## 2. Context Is Useful for These Queries

Many RootLens queries require relationships between concepts rather than isolated phrases.

Examples include:

```text
metrics → detect incident
traces  → localize request
logs    → explain mechanism
```

or:

```text
client span
+
missing server span
+
UNAVAILABLE
+
service discovery
```

A small chunk may contain only one part of this relationship.

The whole document contains enough surrounding context for the embedding to represent the operational intent more accurately.

---

## 3. Word-Based Chunking Can Break Semantic Units

The baseline chunker uses fixed word counts rather than document structure.

A boundary may split:

- a sentence;
- a bullet list;
- an explanation and its qualifier;
- an error code and its interpretation;
- a heading from its supporting paragraph.

Overlap reduces this risk but does not eliminate it.

---

## 4. Max Aggregation Can Produce False Positives

Document score is defined as:

\[
score(D,Q)
=
\max_{c \in D}
similarity(Q,c)
\]

This has a useful property: one excellent passage can make a document rank highly.

However, it also gives every chunk an opportunity to create an accidentally high similarity score.

Documents with more chunks receive more opportunities to produce such a maximum.

This can promote locally similar but globally less relevant documents.

---

## 5. Chunking Removed Useful Document Identity

A whole-document embedding naturally includes:

- the title;
- the service responsibility;
- the overall purpose;
- relationships between multiple paragraphs.

Later chunks may no longer contain the title or enough context to identify what the passage is about.

For operational documentation, document identity can be highly informative.

For example:

```text
Payment Runbook
Metrics Guide
Telemetry Correlation
Service Discovery
```

provide useful semantic context beyond the local sentence content.

---

# Category-Level Comparison

## Multi-Document

```text
Whole:
Recall@3 = 0.5000
nDCG@3   = 0.7885

64 / 16:
Recall@3 = 0.4167
nDCG@3   = 0.4650

128 / 32:
Recall@3 = 0.5000
nDCG@3   = 0.5054
```

Chunking does not improve the main failure mode targeted by the experiment.

---

## Semantic Paraphrase

```text
Whole:
Precision@1 = 1.0000
Recall@3    = 0.6250
nDCG@3      = 0.8203

64 / 16:
Precision@1 = 0.7500
Recall@3    = 0.3750
nDCG@3      = 0.6149

128 / 32:
Precision@1 = 0.7500
Recall@3    = 0.4583
nDCG@3      = 0.6531
```

Whole-document embeddings are substantially better.

This suggests that global context helps BGE infer the intended concept.

---

## Observability

```text
Whole:
Precision@1 = 1.0000
Recall@3    = 0.8889
nDCG@3      = 0.6839

64 / 16:
Precision@1 = 0.6667
Recall@3    = 0.7222
nDCG@3      = 0.6141

128 / 32:
Precision@1 = 0.6667
Recall@3    = 0.6111
nDCG@3      = 0.6333
```

Chunking again provides no benefit.

---

# Important Positive Result

The experiment is useful precisely because the expected technique did not help.

The correct conclusion is not:

> Chunking is bad.

The supported conclusion is:

> Fixed-size chunking is not justified for the current RootLens corpus because the documents are already short, focused, and fully representable by the embedding model.

Chunking may become valuable later when RootLens ingests:

- long runbooks;
- postmortems;
- design documents;
- source-code documentation;
- large incident reports;
- vendor documentation;
- PDFs.

At that point, whole-document embeddings may become too coarse or exceed useful model context.

---

# Decision

Retain whole-document dense retrieval as the current default retrieval granularity.

Current preferred configuration:

```text
retriever:
Dense BGE

model:
BAAI/bge-small-en-v1.5

retrieval unit:
whole document

search:
exact in-memory search

chunking:
disabled for current short operational corpus
```

Do not select:

```text
64 words / 16 overlap
```

or:

```text
128 words / 32 overlap
```

for the current corpus.

Keep the chunking implementation in the repository as an experimental capability for future long-document ingestion.

---

# What This Experiment Changes

Before Experiment 006, one hypothesis was:

```text
incomplete evidence coverage
might be caused by
whole-document semantic dilution
```

The results do not support that hypothesis.

Instead:

```text
whole-document retrieval
>
chunk retrieval
```

on the current corpus.

Therefore the remaining multi-document problem is probably not caused primarily by retrieval-unit size.

We need to investigate whether relevant documents already exist deeper in the dense ranking.

---

# Next Question

Before introducing a reranker, RootLens should answer:

> Are the missing relevant documents already present in a larger dense candidate set?

If the relevant evidence is usually present in the top 10 but not the top 3, reranking may be able to improve ordering.

If the relevant evidence is absent even from the top 10, reranking cannot recover it.

This motivates a candidate-depth analysis.

---

# Next Experiment — Candidate Recall and Reranking Readiness

Experiment 007 should measure whole-document Dense BGE at increasing candidate depths:

```text
Recall@1
Recall@3
Recall@5
Recall@10
Recall@20
```

The analysis should also estimate the maximum Recall@3 that an ideal reranker could achieve when given the top-N dense candidates.

For candidate depth \(N\):

\[
OracleRecall@3(N)
=
\frac{
\min(
3,\,
\text{relevant documents present in top-N}
)
}{
\text{number of relevant documents}
}
\]

This will distinguish two failure modes:

```text
Candidate generation failure
relevant document is not retrieved deeply enough

vs

Ranking failure
relevant document exists in candidates
but is ranked too low
```

That distinction determines whether the next technique should be:

```text
reranking
```

or:

```text
query expansion / multi-query retrieval / query decomposition
```

---

# Final Conclusion

Experiment 006 rejects fixed-size chunking as the preferred retrieval granularity for the current RootLens benchmark.

Whole-document Dense BGE remains clearly stronger across aggregate metrics and the most important query categories.

Chunking:

- reduces Precision@1;
- reduces Recall@3;
- reduces Recall@5;
- reduces MRR;
- reduces nDCG;
- does not solve multi-document evidence coverage.

The next justified step is not more chunk-size tuning.

It is to determine whether current failures are caused by candidate generation or candidate ranking.

The frozen TEST split remains untouched.
