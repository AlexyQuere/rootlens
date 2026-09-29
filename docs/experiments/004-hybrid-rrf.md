# Experiment 004 — Hybrid BM25 + Dense Retrieval with RRF

## Status

Completed

---

## Objective

Evaluate whether combining lexical retrieval and dense semantic retrieval
improves retrieval quality over the strongest single retriever.

The hybrid system combines:

- BM25 lexical retrieval;
- BGE dense semantic retrieval;
- Reciprocal Rank Fusion (RRF).

The hypothesis is:

> Lexical and semantic retrieval may provide complementary signals.
> Reciprocal Rank Fusion may preserve strong exact-term retrieval while
> retaining the semantic gains observed with dense embeddings.

The experiment is evaluated on exactly the same frozen corpus,
evaluation queries, relevance judgments, and metrics as the previous
retrieval experiments.

---

# Experimental Context

The previous experiments established the following baselines:

| Experiment | Retriever |
|---|---|
| Experiment 001 | TF-IDF + cosine similarity |
| Experiment 002 | BM25 |
| Experiment 003 | Dense retrieval using BGE Small English v1.5 |
| Experiment 004 | BM25 + Dense retrieval using Reciprocal Rank Fusion |

The dense retriever from Experiment 003 was the strongest single
retriever on the current calibration benchmark.

The purpose of this experiment is therefore not simply to add another
retrieval technique.

It is to test whether BM25 contributes useful complementary information
when combined with dense semantic retrieval.

---

# Corpus

The corpus is unchanged from the previous experiments.

It contains six operational knowledge documents:

```text
checkout-architecture.md
payment-service.md
grpc-troubleshooting.md
service-discovery.md
observability-guide.md
incident-response-guide.md
```

No document was modified between the TF-IDF, BM25, dense, and hybrid
experiments.

This preserves comparability between retrieval methods.

---

# Evaluation Set

The evaluation set is unchanged from the previous experiments.

It contains eight manually defined queries with explicit relevance
judgments.

The evaluation includes several retrieval situations:

- exact technical identifiers;
- architecture questions;
- troubleshooting questions;
- observability questions;
- semantic paraphrases;
- multi-document relevance.

The benchmark intentionally contains known failure cases from the
previous experiments.

In particular:

```text
q2
gRPC UNAVAILABLE
→ incomplete multi-document recall

q3
correlating logs
→ lexical ranking failure previously corrected by dense retrieval

q6
client failure before downstream server
→ dense retrieval improved multi-document recall

q7
locating a backend service
→ strong lexical vocabulary mismatch
```

---

# Hybrid Architecture

The hybrid retriever combines two independent retrieval systems:

```text
                      Query
                        │
             ┌──────────┴──────────┐
             │                     │
             ▼                     ▼
           BM25                 Dense BGE
             │                     │
             ▼                     ▼
      lexical ranking       semantic ranking
             │                     │
             └──────────┬──────────┘
                        │
                        ▼
             Reciprocal Rank Fusion
                        │
                        ▼
                  final ranking
```

The objective is to combine two different relevance signals.

---

# Lexical Retriever

The lexical component uses BM25.

Configuration:

```text
k1 = 1.5
b = 0.75
```

BM25 provides a relevance signal based primarily on:

- exact lexical overlap;
- rare terms;
- technical identifiers;
- term-frequency saturation;
- document-length normalization.

Examples of terms where lexical retrieval may be valuable include:

```text
PaymentService
UNAVAILABLE
DEADLINE_EXCEEDED
rpc.response.status_code
PlaceOrder
```

---

# Dense Retriever

The dense component uses:

```text
BAAI/bge-small-en-v1.5
```

Configuration:

```text
embedding dimension:
384

query instruction:
enabled

normalized embeddings:
yes

similarity:
dot product

search:
exact in-memory search
```

The query instruction is:

```text
Represent this sentence for searching relevant passages:
```

The dense retriever primarily contributes semantic similarity.

It is intended to handle situations where query and document express
similar concepts using different words.

For example:

```text
locate backend service
```

and:

```text
resolve service name into network addresses
```

have weak exact lexical overlap but strong semantic similarity.

---

# Why Raw Scores Cannot Be Combined Directly

BM25 and dense retrieval produce scores on fundamentally different
scales.

For example:

```text
BM25 score:
10.7371

Dense cosine similarity:
0.7445
```

The values cannot meaningfully be added directly.

For example:

\[
10.7371 + 0.7445
\]

does not represent a meaningful combined relevance score.

Similarly, a weighted sum such as:

\[
0.5 \times BM25
+
0.5 \times Dense
\]

would still be dominated by the different score scales unless an
additional normalization procedure were introduced.

To avoid arbitrary score normalization in this first hybrid baseline,
the system uses rank fusion instead.

---

# Reciprocal Rank Fusion

The hybrid retriever uses Reciprocal Rank Fusion.

For a document \(d\):

\[
RRF(d)
=
\sum_{r \in R}
\frac{1}
{k + rank_r(d)}
\]

where:

- \(R\) is the set of retrievers;
- \(rank_r(d)\) is the position of document \(d\) in retriever \(r\);
- \(k\) is the RRF constant.

The experiment uses:

```text
rrf_k = 60
```

---

# RRF Example

Suppose BM25 returns:

```text
1. A
2. B
3. C
```

and dense retrieval returns:

```text
1. C
2. A
3. D
```

Then:

\[
RRF(A)
=
\frac{1}{61}
+
\frac{1}{62}
\]

while:

\[
RRF(C)
=
\frac{1}{63}
+
\frac{1}{61}
\]

A document that appears near the top of both rankings therefore receives
more support than a document appearing strongly in only one ranking.

---

# Candidate Generation

The final requested number of documents is:

```text
k = 3
```

However, the two underlying retrievers are allowed to retrieve more
candidates before fusion.

The pipeline is conceptually:

```text
BM25
  ↓
top candidate_k
  │
  ├───────────┐
              ▼
             RRF
              ▲
  ├───────────┘
  │
Dense
  ↓
top candidate_k
```

For the current six-document benchmark:

```text
candidate_k = number of documents
```

Therefore all available documents can contribute to the RRF ranking.

At larger scale, a realistic configuration could instead be:

```text
BM25 top 50
Dense top 50
      ↓
     RRF
      ↓
final top 10
```

---

# Evaluation Metrics

The same metrics as the previous experiments are used:

- Precision@1;
- Recall@1;
- Recall@3;
- MRR@3.

No metric definition changed between experiments.

---

# Results

| Retriever | Precision@1 | Recall@1 | Recall@3 | MRR@3 |
|---|---:|---:|---:|---:|
| TF-IDF | 0.7500 | 0.4375 | 0.8750 | 0.8542 |
| BM25 | 0.7500 | 0.4375 | 0.8750 | 0.8542 |
| Dense BGE | **1.0000** | **0.6875** | **0.9375** | **1.0000** |
| Hybrid RRF | **1.0000** | **0.6875** | 0.8750 | **1.0000** |

The hybrid retriever preserved:

```text
Precision@1 = 1.0
MRR@3       = 1.0
```

but reduced:

```text
Recall@3
```

from:

```text
0.9375
```

with dense retrieval to:

```text
0.8750
```

with hybrid retrieval.

---

# Detailed Results

## q1 — Checkout Communication with PaymentService

### Query

```text
How does Checkout communicate with PaymentService?
```

### Relevant Documents

```text
checkout-architecture.md
payment-service.md
```

### Hybrid Ranking

```text
1. payment-service.md         0.0328
2. checkout-architecture.md   0.0323
3. grpc-troubleshooting.md    0.0313
```

### Analysis

Both relevant documents remain first and second.

The result combines strong exact lexical overlap with strong semantic
similarity.

The hybrid system therefore preserves the successful behaviour observed
with both BM25 and dense retrieval.

### Outcome

**Successful**

---

# q2 — gRPC UNAVAILABLE

### Query

```text
What can cause a gRPC request to return UNAVAILABLE?
```

### Relevant Documents

```text
grpc-troubleshooting.md
service-discovery.md
```

### Hybrid Ranking

```text
1. grpc-troubleshooting.md    0.0328
2. checkout-architecture.md   0.0323
3. incident-response-guide.md 0.0313
```

### Analysis

The strongest relevant document remains rank 1.

However:

```text
service-discovery.md
```

still does not appear in the top 3.

This was already a failure for both BM25 and dense retrieval.

RRF does not correct it.

### Outcome

**Partially successful**

The main unresolved multi-document retrieval failure remains present.

---

# q3 — Correlating Logs Across Services

### Query

```text
How can I correlate logs from several services for one request?
```

### Relevant Document

```text
observability-guide.md
```

### Hybrid Ranking

```text
1. observability-guide.md       0.0325
2. service-discovery.md         0.0323
3. incident-response-guide.md   0.0315
```

### Previous Behaviour

BM25:

```text
1. service-discovery.md
2. observability-guide.md
```

Dense:

```text
1. observability-guide.md
```

### Analysis

Dense retrieval corrected the lexical ranking error.

The hybrid system successfully preserves this improvement.

The incorrect BM25 ranking is not strong enough to move
`service-discovery.md` above the semantically relevant
`observability-guide.md`.

### Outcome

**Dense improvement preserved**

---

# q4 — Component Charging the Customer

### Query

```text
Which component charges the customer during checkout?
```

### Relevant Documents

```text
checkout-architecture.md
payment-service.md
```

### Hybrid Ranking

```text
1. checkout-architecture.md   0.0325
2. payment-service.md         0.0325
3. incident-response-guide.md 0.0313
```

### Analysis

Both relevant documents remain first and second.

Their RRF scores are extremely close because both retrievers rank them
highly.

### Outcome

**Successful**

---

# q5 — Investigating an Error-Rate Increase

### Query

```text
What should I inspect after detecting a large error-rate increase?
```

### Relevant Documents

```text
incident-response-guide.md
observability-guide.md
```

### Hybrid Ranking

```text
1. incident-response-guide.md 0.0325
2. observability-guide.md     0.0323
3. payment-service.md         0.0320
```

### Analysis

Both relevant documents appear in the top 2.

The hybrid system provides complete top-3 recall for this query.

### Outcome

**Successful**

---

# q6 — Client Failure Before Downstream Server Receives Request

### Query

```text
Why might a client fail before a downstream server receives the request?
```

### Relevant Documents

```text
grpc-troubleshooting.md
service-discovery.md
```

### Dense Ranking

Dense retrieval previously returned:

```text
1. grpc-troubleshooting.md
2. checkout-architecture.md
3. service-discovery.md
```

Both relevant documents therefore appeared in the top 3.

### Hybrid Ranking

```text
1. grpc-troubleshooting.md  0.0328
2. checkout-architecture.md 0.0323
3. payment-service.md       0.0315
```

### Analysis

The hybrid system pushes:

```text
service-discovery.md
```

outside the top 3.

This is the main regression introduced by RRF.

BM25 ranks other documents strongly enough that their combined
lexical-and-semantic support exceeds the RRF score of
`service-discovery.md`.

The lexical signal therefore introduces noise that partially cancels the
semantic retrieval improvement.

### Outcome

**Regression compared with dense retrieval**

This query explains the drop in aggregate Recall@3.

---

# q7 — Locating a Backend Service

### Query

```text
How does a distributed application locate a backend service?
```

### Relevant Document

```text
service-discovery.md
```

### Hybrid Ranking

```text
1. service-discovery.md       0.0323
2. observability-guide.md     0.0323
3. grpc-troubleshooting.md    0.0318
```

### Previous Behaviour

BM25:

```text
1. grpc-troubleshooting.md
2. observability-guide.md
3. service-discovery.md
```

Dense:

```text
1. service-discovery.md
```

### Analysis

This query is the strongest vocabulary-mismatch case in the current
benchmark.

Dense retrieval corrected the lexical failure.

RRF preserves the dense improvement and keeps the relevant document at
rank 1.

However, the RRF score difference between the first two documents is
very small.

### Outcome

**Dense semantic improvement preserved**

---

# q8 — Error Is Not Automatically the Root Cause

### Query

```text
Why should the first error I find not automatically be called the root cause?
```

### Relevant Document

```text
incident-response-guide.md
```

### Hybrid Ranking

```text
1. incident-response-guide.md 0.0328
2. grpc-troubleshooting.md    0.0315
3. checkout-architecture.md   0.0313
```

### Analysis

Both lexical and dense retrieval strongly support the relevant
document.

RRF therefore preserves the correct rank-1 result.

### Outcome

**Successful**

---

# Why RRF Scores Are Around 0.03

The resulting hybrid scores are much smaller than either BM25 or dense
similarity scores.

For example:

```text
0.0328
0.0325
0.0323
```

This is expected.

A document ranked first by both retrievers receives:

\[
\frac{1}{60+1}
+
\frac{1}{60+1}
\]

which gives:

\[
\frac{2}{61}
\approx
0.03279
\]

Similarly, a document ranked second by both retrievers receives:

\[
\frac{2}{62}
\approx
0.03226
\]

These numbers are fusion scores only.

They are not probabilities.

They are not calibrated confidence values.

They should only be interpreted as values used to construct the final
ranking.

---

# Effect of `rrf_k = 60`

The RRF constant used in this experiment is:

```text
60
```

With such a value, differences between nearby ranks are deliberately
small.

For example:

\[
\frac{1}{61}
\approx
0.01639
\]

while:

\[
\frac{1}{66}
\approx
0.01515
\]

Therefore, even rank 1 and rank 6 receive relatively similar individual
RRF contributions.

On the current corpus of only six documents, this strongly compresses
rank differences.

However, the experiment does not tune `rrf_k`.

Changing it to optimize eight evaluation queries would create a high
risk of overfitting.

A larger benchmark is required before evaluating alternative fusion
parameters.

---

# Comparison with Dense Retrieval

Dense retrieval remains stronger on the current benchmark.

Both systems obtain:

```text
Precision@1 = 1.0
Recall@1    = 0.6875
MRR@3       = 1.0
```

but dense retrieval obtains:

```text
Recall@3 = 0.9375
```

while hybrid RRF obtains:

```text
Recall@3 = 0.8750
```

The hybrid system therefore introduces additional complexity without
providing a measurable improvement.

It instead causes one retrieval regression.

---

# Main Failure Analysis

The experiment demonstrates an important point:

> Complementary retrieval methods do not automatically produce a better
> combined retriever.

A lexical ranking can introduce noise into a semantic ranking.

For q6:

```text
Dense
→ service-discovery.md rank 3
```

but:

```text
BM25 + Dense + RRF
→ service-discovery.md outside top 3
```

Therefore:

```text
additional signal
≠
useful signal
```

The quality of fusion depends on the quality and complementarity of the
individual ranking systems.

---

# Decision

The hybrid BM25 + Dense RRF retriever is **not selected as the default
RootLens retrieval architecture at this stage**.

The current preferred retriever remains:

```text
BAAI/bge-small-en-v1.5
```

using exact in-memory dense retrieval.

The current architecture decision is therefore:

```text
TF-IDF
    ↓
educational baseline

BM25
    ↓
lexical baseline

Dense BGE
    ↓
current preferred retriever

BM25 + Dense + RRF
    ↓
implemented experimental alternative
not selected
```

The RRF implementation should remain in the repository because it is
useful for future comparison when the corpus becomes larger and more
heterogeneous.

---

# Why BM25 Is Not Removed

Although BM25 does not improve the current benchmark, it remains useful
as a reference implementation.

Operational systems often contain exact strings such as:

```text
PaymentService/Charge
UNAVAILABLE
DEADLINE_EXCEEDED
checkout-v3.1.0
rpc.response.status_code
trace IDs
span IDs
configuration keys
```

A larger corpus containing many such identifiers may increase the value
of lexical retrieval.

Therefore, the correct conclusion is not:

> BM25 is useless.

The supported conclusion is:

> BM25 does not provide enough complementary signal on the current
> six-document calibration corpus to justify RRF fusion.

---

# Methodological Lesson

The experiment reinforces the project principle:

```text
baseline
    ↓
identify a failure
    ↓
introduce a technique intended to solve it
    ↓
measure
    ↓
retain only if justified
```

The correct engineering decision is not to keep an architecture simply
because it is more sophisticated.

Complexity must earn its place through measured improvements.

In this experiment:

```text
Hybrid complexity
    ↑

Retrieval performance
    ↔ / ↓
```

Therefore the additional complexity is not currently justified.

---

# Limitations

The current benchmark remains very small:

```text
documents = 6
queries   = 8
```

This is sufficient for learning retrieval fundamentals and detecting
clear failure modes.

It is not sufficient for strong conclusions about production retrieval
performance.

The current results must therefore be treated as:

```text
calibration evidence
```

rather than:

```text
general benchmark evidence
```

---

# Next Step

Further retrieval architecture optimization should stop temporarily.

The next priority is to build a larger and more challenging retrieval
benchmark.

The target should be approximately:

```text
20–30 operational documents
30–50 evaluation queries
```

The expanded benchmark should include several query families.

---

## Exact Technical Identifier Queries

Examples:

```text
Which component calls PaymentService/Charge?
```

```text
What does rpc.response.status_code represent?
```

```text
Where is DEADLINE_EXCEEDED documented?
```

These queries test whether lexical retrieval retains an advantage for
rare exact identifiers.

---

## Semantic Paraphrases

Examples:

```text
How does an application find another backend?
```

versus documentation using:

```text
service discovery
DNS
resolution
network address
```

These queries test dense semantic retrieval.

---

## Multi-Document Queries

Examples:

```text
What evidence should I combine to determine whether a checkout failure
comes from service discovery or from PaymentService business logic?
```

These queries require complementary evidence from multiple documents.

They are especially important for the future RootLens RAG system.

---

## Hard Negatives

The corpus should contain documents that share vocabulary with the query
but are not actually relevant.

For example:

```text
payment-service.md
payment-monitoring.md
payment-retries.md
checkout-payment-flow.md
```

A retriever should distinguish between documents that merely share words
and documents that actually answer the question.

---

## Unrelated Negative Documents

Additional operational documentation should also be included for
services such as:

```text
shipping
cart
currency
recommendation
frontend
product catalog
feature flags
telemetry collector
```

This prevents the benchmark from becoming artificially easy.

---

## Document-Length Diversity

Future documents should include:

```text
short runbook entries
medium architecture notes
long troubleshooting guides
incident retrospectives
configuration documentation
```

This will provide a more meaningful test of BM25 document-length
normalization and future chunking strategies.

---

# Future Comparison

Once Retrieval Benchmark v2 exists, all four retrievers should be
reevaluated:

```text
TF-IDF
BM25
Dense BGE
Hybrid RRF
```

using the same benchmark.

Only then should the project evaluate additional retrieval complexity
such as:

```text
chunking
metadata filtering
query rewriting
reranking
hybrid weighting
cross-encoders
```

After retrieval quality is sufficiently understood, RootLens can move
to the next major stage:

```text
retrieval
    ↓
context construction
    ↓
LLM generation
    ↓
Basic RAG
    ↓
RAG evaluation
```

---

# Final Conclusion

On the current RootLens calibration benchmark, Reciprocal Rank Fusion
successfully preserves the main semantic gains of dense retrieval but
does not improve overall retrieval quality.

The hybrid system achieves:

```text
Precision@1 = 1.0000
Recall@1    = 0.6875
Recall@3    = 0.8750
MRR@3       = 1.0000
```

compared with dense retrieval:

```text
Precision@1 = 1.0000
Recall@1    = 0.6875
Recall@3    = 0.9375
MRR@3       = 1.0000
```

The additional lexical signal causes a top-3 recall regression on q6.

Therefore:

> Dense BGE remains the preferred RootLens retriever on the current
> benchmark, while BM25 + RRF remains an experimental baseline to
> reevaluate on a larger and more realistic corpus.
