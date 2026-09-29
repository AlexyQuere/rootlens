# Experiment 002 — BM25 Retrieval Baseline

## Status

Completed

## Objective

Compare BM25 against the frozen TF-IDF Baseline v1 on the same RootLens retrieval benchmark.

The experiment tests whether BM25's explicit term-frequency saturation and document-length normalization improve ranking quality over TF-IDF with cosine similarity.

---

## Experimental Setup

### Corpus

The corpus is unchanged from Experiment 001 and contains 6 operational knowledge documents:

- `checkout-architecture.md`
- `payment-service.md`
- `grpc-troubleshooting.md`
- `service-discovery.md`
- `observability-guide.md`
- `incident-response-guide.md`

### Evaluation set

The evaluation set is unchanged from Experiment 001 and contains 8 manually defined queries with explicit relevance judgments.

### BM25 configuration

- `k1 = 1.5`
- `b = 0.75`
- lowercase lexical tokenization
- no stemming
- no lemmatization
- no stop-word removal
- no query rewriting
- no embeddings
- no reranking

### Evaluation metrics

- Precision@1
- Recall@1
- Recall@3
- MRR@3

---

## Results

| Metric | TF-IDF v1 | BM25 |
|---|---:|---:|
| Precision@1 | 0.7500 | 0.7500 |
| Recall@1 | 0.4375 | 0.4375 |
| Recall@3 | 0.8750 | 0.8750 |
| MRR@3 | 0.8542 | 0.8542 |

BM25 produced exactly the same aggregate retrieval metrics as TF-IDF on this benchmark.

---

## Query-Level Comparison

### q1 — Checkout communication with PaymentService

Relevant documents:

- `checkout-architecture.md`
- `payment-service.md`

TF-IDF ranking:

1. `checkout-architecture.md`
2. `payment-service.md`
3. `grpc-troubleshooting.md`

BM25 ranking:

1. `payment-service.md`
2. `checkout-architecture.md`
3. `grpc-troubleshooting.md`

BM25 changed the order of the two relevant documents but did not change any evaluation metric.

This query is dominated by strong exact lexical matches such as `Checkout` and `PaymentService`.

---

### q2 — gRPC UNAVAILABLE

Relevant documents:

- `grpc-troubleshooting.md`
- `service-discovery.md`

BM25 ranking:

1. `grpc-troubleshooting.md`
2. `checkout-architecture.md`
3. `incident-response-guide.md`

The first relevant document remained correctly ranked first.

However, `service-discovery.md` was still missing from the top 3.

BM25 did not improve multi-document recall for this query.

---

### q3 — Correlating logs across services

Relevant document:

- `observability-guide.md`

BM25 ranking:

1. `service-discovery.md`
2. `observability-guide.md`
3. `checkout-architecture.md`

The relevant document remained at rank 2.

The top-1 ranking failure observed with TF-IDF was therefore not corrected by BM25.

---

### q4 — Component charging the customer

Relevant documents:

- `checkout-architecture.md`
- `payment-service.md`

BM25 ranking:

1. `checkout-architecture.md`
2. `payment-service.md`
3. `observability-guide.md`

The two relevant documents remained first and second.

This query has strong lexical overlap with the corpus and is easy for both lexical methods.

---

### q5 — Investigating a large error-rate increase

Relevant documents:

- `incident-response-guide.md`
- `observability-guide.md`

BM25 ranking:

1. `observability-guide.md`
2. `incident-response-guide.md`
3. `payment-service.md`

Both relevant documents remained in the top 2.

BM25 preserved the successful TF-IDF behaviour.

---

### q6 — Client fails before downstream server receives request

Relevant documents:

- `grpc-troubleshooting.md`
- `service-discovery.md`

BM25 ranking:

1. `grpc-troubleshooting.md`
2. `checkout-architecture.md`
3. `payment-service.md`

Only one of the two relevant documents was retrieved in the top 3.

BM25 therefore did not improve the incomplete recall observed with TF-IDF.

---

### q7 — Locating a backend service

Relevant document:

- `service-discovery.md`

BM25 ranking:

1. `grpc-troubleshooting.md`
2. `observability-guide.md`
3. `service-discovery.md`

The relevant document remained at rank 3.

This query remains the clearest vocabulary-mismatch example in the benchmark.

The query uses terms such as:

```text
locate
backend
```

while the relevant document uses related expressions such as:

```text
service discovery
resolve
endpoint
network address
```

BM25 remains a lexical method and therefore does not inherently model these semantic relationships.

---

### q8 — Error versus root cause

Relevant document:

- `incident-response-guide.md`

BM25 ranking:

1. `incident-response-guide.md`
2. `checkout-architecture.md`
3. `observability-guide.md`

The relevant document remained first by a large margin.

Strong lexical overlap makes this query easy for both TF-IDF and BM25.

---

## Interpretation

### BM25 did not improve the benchmark

The aggregate metrics are identical to TF-IDF:

```text
Precision@1 = 0.7500
Recall@1    = 0.4375
Recall@3    = 0.8750
MRR@3       = 0.8542
```

This does not imply that BM25 is equivalent to TF-IDF in general.

The current benchmark is very small and has characteristics that reduce the practical impact of BM25's main advantages.

---

## Why BM25 Did Not Improve Here

### Limited term-frequency variation

The documents are short and most important technical terms occur only once or a few times.

BM25's term-frequency saturation therefore has little opportunity to change the ranking.

### Similar document lengths

The six documents have relatively similar lengths.

BM25's explicit length normalization therefore has limited influence.

### Lexical overlap dominates the benchmark

Queries such as q1, q4 and q8 contain terms that also occur directly in the relevant documents.

Both TF-IDF and BM25 handle these cases well.

### The main remaining failure is semantic

q7 is mainly a vocabulary-mismatch problem.

BM25 cannot inherently infer:

```text
locate ≈ resolve
backend ≈ service
```

because it is still a lexical retrieval method.

---

## Important Scoring Note

BM25 scores and TF-IDF cosine scores are not directly comparable.

For example:

```text
TF-IDF cosine score: 0.4452
BM25 score:          10.7371
```

does not mean BM25 is "24 times more confident".

The two algorithms use different scoring functions and score scales.

Only rankings and evaluation metrics should be compared across retrievers.

---

## Decision

BM25 is retained as an important lexical baseline, but it does not replace TF-IDF on the basis of this experiment.

No BM25 hyperparameter tuning will be performed on the current 8-query benchmark.

Tuning `k1` and `b` on such a small evaluation set would create a high risk of overfitting and would not address the main observed failure mode: semantic vocabulary mismatch.

---

## Lessons Learned

The experiment demonstrates that increasing algorithmic sophistication does not automatically improve retrieval quality.

A more advanced retrieval method should be introduced to solve a measured limitation rather than because it is conventionally considered stronger.

The current benchmark suggests that the next important limitation is semantic matching rather than lexical term weighting.

---

## Next Experiment

The next experiment should introduce a dense embedding retriever while keeping the following fixed:

- corpus;
- evaluation queries;
- relevance judgments;
- evaluation metrics.

The main hypothesis is:

> Dense retrieval may improve queries where the query and relevant document express similar concepts using different vocabulary.

Particular attention should be paid to:

- q3 — relevant document at rank 2;
- q6 — incomplete multi-document recall;
- q7 — semantic vocabulary mismatch.

Dense retrieval should also be checked for regressions on exact technical identifier queries such as q1, q2 and q8.

The eventual objective is not to assume that dense retrieval replaces lexical retrieval, but to determine experimentally whether the two methods have complementary strengths that justify hybrid retrieval.
