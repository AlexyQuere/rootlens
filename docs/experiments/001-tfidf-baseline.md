# Experiment 001 — TF-IDF Retrieval Baseline

## Status

Completed

## Objective

Establish the first measured retrieval baseline for RootLens before
introducing BM25, dense embeddings, hybrid retrieval or reranking.

---

## Setup

### Corpus

6 operational knowledge documents:

- `checkout-architecture.md`
- `payment-service.md`
- `grpc-troubleshooting.md`
- `service-discovery.md`
- `observability-guide.md`
- `incident-response-guide.md`

### Evaluation set

8 manually defined queries with explicit relevance judgments.

### Retriever

TF-IDF with:

- lowercase lexical tokenization;
- raw term frequency;
- unsmoothed IDF;
- cosine similarity;
- no stemming;
- no lemmatization;
- no stop-word removal;
- no embeddings;
- no reranking.

---

## Results

| Metric | Score |
|---|---:|
| Precision@1 | 0.7500 |
| Recall@1 | 0.4375 |
| Recall@3 | 0.8750 |
| MRR@3 | 0.8542 |

---

## Per-query observations

### q1 — Checkout communication with PaymentService

Relevant documents were ranked first and second.

TF-IDF performed well because the query contains exact technical
identifiers such as `Checkout` and `PaymentService`.

### q2 — gRPC UNAVAILABLE

`grpc-troubleshooting.md` was ranked first.

Exact technical vocabulary such as `gRPC` and `UNAVAILABLE` was highly
effective for lexical retrieval.

However, the second relevant document, `service-discovery.md`, was not
present in the top 3.

### q3 — Correlating logs across services

`observability-guide.md` was relevant but appeared at rank 2.

`service-discovery.md` incorrectly appeared at rank 1.

This is a ranking failure rather than a complete retrieval failure.

### q4 — Component charging the customer

The two relevant architecture documents were ranked first and second.

The query had strong lexical overlap with the knowledge corpus.

### q5 — Investigating an error-rate increase

Both relevant documents appeared in the top 2.

This was a successful multi-document retrieval case.

### q6 — Client failure before downstream server receives request

`grpc-troubleshooting.md` was ranked first.

However, `service-discovery.md` did not appear in the top 3 despite
being relevant.

This reduced recall for the query.

### q7 — Locating a backend service

`service-discovery.md` was only ranked third.

This is the clearest vocabulary-mismatch example in the current
benchmark.

The query uses terms such as:

- `locate`
- `backend`

while the document uses related but different expressions such as:

- `service discovery`
- `resolve`
- `endpoint`
- `network address`

TF-IDF cannot directly model these semantic relationships.

### q8 — Error versus root cause

`incident-response-guide.md` was ranked first with a large margin.

The query and document share highly discriminative lexical terms such
as:

- `error`
- `automatically`
- `root cause`

This is a strong lexical retrieval case.

---

## Strengths

The baseline performs well when:

- query terminology closely matches the documentation;
- exact service names are present;
- technical status codes are present;
- rare identifiers provide strong lexical signals.

Examples include:

- `PaymentService`
- `Checkout`
- `UNAVAILABLE`
- `root cause`

---

## Weaknesses

### Vocabulary mismatch

Lexical retrieval cannot inherently understand relations such as:

```text
locate ≈ resolve
backend ≈ service
billing ≈ payment