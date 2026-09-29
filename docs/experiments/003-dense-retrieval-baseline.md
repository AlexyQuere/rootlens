# Experiment 003 — Dense Retrieval Baseline

## Status

Completed

## Objective

Evaluate dense semantic retrieval on the same frozen RootLens benchmark used for the TF-IDF and BM25 experiments.

The purpose of this experiment is to test whether a dense embedding model can improve retrieval when the query and the relevant document express the same concept using different vocabulary.

The main hypothesis is:

> Dense retrieval should improve semantic and paraphrase queries, especially cases affected by lexical vocabulary mismatch, while ideally preserving performance on exact technical queries.

---

## Experimental Setup

### Corpus

The corpus is unchanged from Experiments 001 and 002.

It contains 6 operational knowledge documents:

- `checkout-architecture.md`
- `payment-service.md`
- `grpc-troubleshooting.md`
- `service-discovery.md`
- `observability-guide.md`
- `incident-response-guide.md`

### Evaluation Set

The evaluation set is unchanged and contains 8 manually defined queries with explicit relevance judgments.

The same corpus, queries, qrels, and evaluation metrics are used to preserve comparability across experiments.

---

## Dense Retriever

### Embedding Model

```text
BAAI/bge-small-en-v1.5
```

### Embedding Dimension

```text
384
```

### Query Instruction

Queries are encoded using:

```text
Represent this sentence for searching relevant passages:
```

Documents are encoded without the query instruction.

### Embedding Normalization

Embeddings are L2-normalized.

Therefore cosine similarity is equivalent to a dot product:

\[
\cos(q,d)=q\cdot d
\]

because:

\[
\|q\|=\|d\|=1
\]

### Retrieval Infrastructure

No vector database is used.

The benchmark contains only 6 documents, so document embeddings are stored in memory and exact similarity search is performed directly.

The retrieval pipeline is:

```text
documents
    ↓
BGE encoder
    ↓
normalized document embeddings
    ↓
stored in memory

query
    ↓
BGE encoder
    ↓
normalized query embedding
    ↓
dot product with all document embeddings
    ↓
ranking
    ↓
top-k documents
```

### Device

```text
CPU
```

No GPU or Apple MPS acceleration is required for this benchmark.

---

## Evaluation Metrics

The same metrics as the previous experiments are used:

- Precision@1
- Recall@1
- Recall@3
- MRR@3

---

## Results

| Metric | TF-IDF v1 | BM25 | Dense BGE |
|---|---:|---:|---:|
| Precision@1 | 0.7500 | 0.7500 | **1.0000** |
| Recall@1 | 0.4375 | 0.4375 | **0.6875** |
| Recall@3 | 0.8750 | 0.8750 | **0.9375** |
| MRR@3 | 0.8542 | 0.8542 | **1.0000** |

Dense retrieval improved every aggregate metric on the current benchmark.

Because the evaluation contains only 8 queries, these results should be interpreted as calibration evidence rather than a general performance claim.

---

# Query-Level Analysis

## q1 — Checkout Communication with PaymentService

### Query

```text
How does Checkout communicate with PaymentService?
```

### Relevant Documents

- `checkout-architecture.md`
- `payment-service.md`

### Dense Ranking

```text
1. payment-service.md         0.8097
2. checkout-architecture.md   0.7977
3. service-discovery.md       0.5674
```

### Analysis

Both relevant documents were ranked first and second.

This query contains strong technical identifiers such as:

```text
Checkout
PaymentService
```

Lexical retrieval already performed well on this query.

The dense retriever preserved that performance.

### Outcome

**Successful**

---

## q2 — gRPC UNAVAILABLE

### Query

```text
What can cause a gRPC request to return UNAVAILABLE?
```

### Relevant Documents

- `grpc-troubleshooting.md`
- `service-discovery.md`

### Dense Ranking

```text
1. grpc-troubleshooting.md    0.8672
2. checkout-architecture.md   0.6514
3. payment-service.md         0.6417
```

### Analysis

The strongest relevant document was correctly ranked first.

However, the second relevant document:

```text
service-discovery.md
```

was still missing from the top 3.

This means the query still has incomplete multi-document recall.

### Outcome

**Partially successful**

This remains the main unresolved retrieval failure in the current benchmark.

---

## q3 — Correlating Logs Across Services

### Query

```text
How can I correlate logs from several services for one request?
```

### Relevant Document

- `observability-guide.md`

### Dense Ranking

```text
1. observability-guide.md       0.7308
2. incident-response-guide.md   0.6488
3. service-discovery.md         0.6451
```

### Comparison with Lexical Retrieval

TF-IDF and BM25 ranked:

```text
1. service-discovery.md
2. observability-guide.md
```

Dense retrieval moved the correct document to rank 1.

### Interpretation

The dense representation appears to capture the semantic relation between:

```text
correlate logs from several services
```

and documentation discussing:

```text
trace IDs
same distributed request
cross-service log correlation
```

even when the exact vocabulary is not identical.

### Outcome

**Improved by dense retrieval**

---

## q4 — Component Charging the Customer

### Query

```text
Which component charges the customer during checkout?
```

### Relevant Documents

- `checkout-architecture.md`
- `payment-service.md`

### Dense Ranking

```text
1. payment-service.md         0.7411
2. checkout-architecture.md   0.7008
3. incident-response-guide.md 0.4774
```

### Analysis

Both relevant documents are ranked first and second.

The dense retriever preserved the strong performance already observed with lexical retrieval.

### Outcome

**Successful**

---

## q5 — Investigating a Large Error-Rate Increase

### Query

```text
What should I inspect after detecting a large error-rate increase?
```

### Relevant Documents

- `incident-response-guide.md`
- `observability-guide.md`

### Dense Ranking

```text
1. incident-response-guide.md   0.6826
2. payment-service.md           0.5965
3. observability-guide.md       0.5937
```

### Analysis

Both relevant documents appear in the top 3.

However, one irrelevant document appears between them.

Therefore:

```text
Recall@3 = 1
```

but the ranking is not perfect.

### Outcome

**Successful at top-3 recall**

---

## q6 — Client Failure Before Server Receives Request

### Query

```text
Why might a client fail before a downstream server receives the request?
```

### Relevant Documents

- `grpc-troubleshooting.md`
- `service-discovery.md`

### Dense Ranking

```text
1. grpc-troubleshooting.md    0.6814
2. checkout-architecture.md   0.6767
3. service-discovery.md       0.6629
```

### Comparison with Lexical Retrieval

TF-IDF and BM25 retrieved only:

```text
grpc-troubleshooting.md
```

among the top 3 relevant documents.

Dense retrieval also recovered:

```text
service-discovery.md
```

at rank 3.

### Interpretation

Dense retrieval improved multi-document recall by connecting the query with concepts such as:

```text
client failure
downstream server
service resolution
network destination
```

### Outcome

**Improved by dense retrieval**

---

## q7 — Locating a Backend Service

### Query

```text
How does a distributed application locate a backend service?
```

### Relevant Document

- `service-discovery.md`

### Dense Ranking

```text
1. service-discovery.md         0.8020
2. observability-guide.md       0.6724
3. incident-response-guide.md   0.6342
```

### Comparison with Lexical Retrieval

BM25 ranked:

```text
1. grpc-troubleshooting.md
2. observability-guide.md
3. service-discovery.md
```

Dense retrieval moved the relevant document from rank 3 to rank 1.

### Interpretation

This query is the clearest example of vocabulary mismatch.

The query contains:

```text
locate
backend service
```

while the relevant document uses expressions such as:

```text
service discovery
resolve
service instances
network addresses
endpoint configuration
```

Lexical methods do not inherently know that these concepts are related.

Dense embeddings successfully represented the semantic similarity.

### Outcome

**Strongly improved by dense retrieval**

---

## q8 — Error Is Not Automatically the Root Cause

### Query

```text
Why should the first error I find not automatically be called the root cause?
```

### Relevant Document

- `incident-response-guide.md`

### Dense Ranking

```text
1. incident-response-guide.md   0.7445
2. service-discovery.md         0.6117
3. grpc-troubleshooting.md      0.5481
```

### Analysis

The relevant document remained at rank 1.

Lexical retrieval already performed very well because of exact overlap with terms such as:

```text
error
automatically
root cause
```

Dense retrieval did not introduce a regression.

### Outcome

**Successful**

---

# Aggregate Interpretation

## Precision@1

Dense retrieval achieved:

\[
Precision@1=1.0
\]

The top-ranked result was relevant for all 8 evaluation queries.

This improves over:

\[
0.75
\]

for both TF-IDF and BM25.

---

## Recall@1

Dense retrieval achieved:

\[
Recall@1=0.6875
\]

This remains below 1 because several queries have multiple relevant documents.

A top-1 retrieval can recover at most one of them.

---

## Recall@3

Dense retrieval achieved:

\[
Recall@3=0.9375
\]

This improves over:

\[
0.875
\]

for TF-IDF and BM25.

The remaining loss is mainly caused by q2, where `service-discovery.md` is still absent from the top 3.

---

## MRR@3

Dense retrieval achieved:

\[
MRR@3=1.0
\]

For every evaluation query, at least one relevant document appears at rank 1.

---

# Main Strengths Observed

Dense retrieval improved the benchmark particularly when relevance depended on semantic similarity rather than exact token overlap.

The strongest examples were:

```text
q3 — log correlation
q6 — downstream request failure
q7 — service discovery paraphrase
```

In particular, q7 confirms that dense representations can address vocabulary mismatch such as:

```text
locate ≈ resolve
backend service ≈ service instance / endpoint
```

---

# Remaining Weaknesses

## Incomplete Multi-Document Recall

q2 remains unresolved.

The query:

```text
What can cause a gRPC request to return UNAVAILABLE?
```

has two relevant sources:

- `grpc-troubleshooting.md`
- `service-discovery.md`

Dense retrieval finds the first but does not place the second in the top 3.

This suggests that even strong semantic retrieval may fail to collect all complementary evidence needed for a complete answer.

---

## Dense Scores Are Not Probabilities

Scores such as:

```text
0.8097
0.7308
0.6629
```

represent embedding similarity.

They must not be interpreted as calibrated probabilities or confidence values.

For example:

```text
score = 0.80
```

does not mean:

```text
80% probability of relevance
```

Scores are primarily useful for ranking documents within the same query.

---

## Exact Technical Terms Still Matter

Dense retrieval did not regress on the current exact-term queries.

However, this benchmark is too small to conclude that dense retrieval always preserves lexical strengths.

Operational corpora often contain rare identifiers such as:

```text
PaymentService
UNAVAILABLE
DEADLINE_EXCEEDED
rpc.response.status_code
traceId
```

Lexical retrieval may remain particularly valuable for such terms.

This motivates evaluating hybrid retrieval rather than assuming that dense retrieval should replace BM25.

---

# Methodological Interpretation

The correct conclusion is not:

> Dense retrieval is generally better than BM25.

The supported conclusion is:

> On the current 8-query RootLens calibration benchmark, dense retrieval with `BAAI/bge-small-en-v1.5` improved all measured aggregate metrics over TF-IDF and BM25, with the clearest gains occurring on semantic/paraphrase queries such as q3 and q7.

Because the benchmark is small, additional queries are required before making broader claims.

---

# Architectural Implications

The experiment changes the nature of the RootLens retrieval architecture.

Lexical retrieval represents documents using explicit vocabulary terms.

Dense retrieval represents them using learned semantic vectors.

The two methods therefore capture different signals:

```text
BM25
→ exact lexical overlap
→ technical identifiers
→ rare error codes
→ explicit names

Dense retrieval
→ semantic similarity
→ paraphrases
→ vocabulary mismatch
→ concept-level matching
```

This suggests that the next useful experiment is not necessarily to choose one method over the other.

Instead, RootLens should test whether combining both signals improves retrieval.

---

# Decision

Dense retrieval is retained as the current strongest single retriever on the calibration benchmark.

Configuration:

```text
model:
BAAI/bge-small-en-v1.5

embedding dimension:
384

query instruction:
enabled

normalized embeddings:
yes

similarity:
dot product on normalized embeddings

vector database:
none

search:
exact in-memory search
```

No vector database is introduced yet because the corpus is far too small to justify approximate nearest-neighbor infrastructure.

---

# Next Experiment

The next experiment will evaluate **hybrid retrieval**.

The two candidate rankings will come from:

```text
BM25
+
Dense BGE retrieval
```

Raw scores cannot be directly combined because they use different scales:

```text
BM25 score:
10.7371

Dense score:
0.7445
```

Therefore, the initial fusion method will use **Reciprocal Rank Fusion (RRF)**.

The hypothesis is:

> Combining lexical and semantic rankings may preserve exact technical matching while retaining dense retrieval's gains on semantic queries.

Particular attention should be paid to:

- q2 — incomplete multi-document recall;
- q3 — semantic ranking;
- q6 — multi-document recall;
- q7 — vocabulary mismatch;
- exact identifier queries such as q1 and q8.

The corpus, queries, qrels, and evaluation metrics must remain unchanged.
