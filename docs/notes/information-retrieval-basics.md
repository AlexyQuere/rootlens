# Information Retrieval Basics

## Status

Learning note for **RootLens — Milestone 1: Information Retrieval**

## Objective

This note introduces the foundations of Information Retrieval (IR) before adding embeddings, vector databases, hybrid retrieval, reranking, RAG, or agents.

The central problem is:

> Given a query and a collection of documents, how can a system rank documents by relevance?

For RootLens, this will eventually mean retrieving operational knowledge such as:

- architecture documentation;
- service documentation;
- runbooks;
- troubleshooting guides;
- configuration documentation;
- historical incident reports.

The first milestone intentionally focuses on **retrieval without an LLM** so that retrieval quality can be measured independently from generation quality.

---

# 1. Information Retrieval and RAG

A basic information retrieval system is:

```text
Documents
   ↓
Indexing
   ↓
Search index

Query
   ↓
Query processing
   ↓
Scoring
   ↓
Ranking
   ↓
Top-k documents
```

A RAG system adds generation:

```text
Query
  ↓
Retriever
  ↓
Relevant passages
  ↓
LLM
  ↓
Grounded answer
```

This distinction matters because RAG can fail in two very different ways:

```text
Bad retrieval
→ relevant evidence never reaches the LLM

Good retrieval + bad generation
→ evidence is available but the LLM uses it badly
```

Therefore, retrieval must be evaluated independently before generation is introduced.

For RootLens:

```text
Live operational evidence
(metrics, traces, logs)
        ↓
deterministic tools / APIs

Operational knowledge
(docs, runbooks, incidents)
        ↓
information retrieval / RAG
```

Not every data source should be embedded or stored in a vector database.

---

# 2. Core Terminology

## Corpus

A **corpus** is the full collection of searchable documents.

Let:

\[
\mathcal{D}=\{d_1,d_2,\ldots,d_N\}
\]

where \(N\) is the number of documents.

Example:

```text
Corpus
├── checkout-service.md
├── payment-service.md
├── grpc-troubleshooting.md
└── incident-handbook.md
```

## Document

A document is one retrievable unit. It may be:

- a whole file;
- a section;
- a paragraph;
- a chunk;
- an incident report;
- a runbook entry.

The choice of retrieval unit later becomes the **chunking problem**.

## Query

A **query** represents the user's information need.

Example:

```text
payment service unavailable
```

We denote it by:

\[
q
\]

## Relevance

A document is relevant when it contains information useful for satisfying the information need.

Relevance is not identical to exact word overlap.

Example:

```text
Query:
payment service unavailable

Document:
checkout cannot reach the billing backend
```

A human may consider the document relevant even though the exact vocabulary differs.

This leads to the distinction between lexical and semantic retrieval.

---

# 3. Text Preprocessing

A simplified preprocessing pipeline is:

```text
Raw text
   ↓
Normalization
   ↓
Tokenization
   ↓
Optional filtering / linguistic processing
   ↓
Terms
```

Normalization may include:

- lowercasing;
- Unicode normalization;
- punctuation handling;
- whitespace normalization;
- domain-specific transformations.

Example:

```text
"Payment Service UNAVAILABLE!"
```

may become:

```text
"payment service unavailable"
```

For technical corpora, aggressive normalization can destroy useful information.

RootLens will contain terms such as:

```text
PaymentService
payment-service
rpc.response.status_code
HTTP_500
gRPC
trace_id
```

Preprocessing should therefore be benchmarked rather than chosen blindly.

---

# 4. Tokenization

Tokenization splits text into tokens.

Example:

```text
"Payment service unavailable"
```

becomes:

```python
["payment", "service", "unavailable"]
```

Conceptually:

\[
\text{text}\rightarrow[t_1,t_2,\ldots,t_m]
\]

Technical text creates special choices.

A tokenizer may split:

```text
rpc.response.status_code
```

into:

```text
rpc
response
status
code
```

or preserve:

```text
rpc.response.status_code
```

Similarly:

```text
PaymentService
```

could remain one token or become:

```text
payment
service
```

There is no universally correct choice. The correct question is:

> Which tokenization gives the best retrieval performance on our benchmark?

---

# 5. Stop Words, Stemming and Lemmatization

## Stop words

Common terms such as:

```text
the
a
is
of
and
```

often carry little discriminative information.

Traditional systems sometimes remove them. However, IDF already gives very common terms low weight, and removing tokens may damage exact phrases.

RootLens should not remove terms without measuring the effect.

## Stemming

Stemming uses heuristic rules to reduce related word forms to a common stem.

Example:

```text
connect
connected
connecting
connection
```

may be mapped approximately to a common form.

This can improve recall but can also merge unrelated forms.

## Lemmatization

Lemmatization maps inflected forms to linguistic dictionary forms.

Example:

```text
running → run
services → service
```

For the first RootLens baseline, simple tokenization is preferable. More complex linguistic preprocessing should only be added if experiments justify it.

---

# 6. Bag of Words

The **Bag of Words (BoW)** model represents text by which vocabulary terms occur, while ignoring word order.

Consider:

```text
D1 = "payment service"
D2 = "payment service unavailable"
D3 = "shipping service"
```

Vocabulary:

```text
payment
service
unavailable
shipping
```

Using that order:

\[
D_1=[1,1,0,0]
\]

\[
D_2=[1,1,1,0]
\]

\[
D_3=[0,1,0,1]
\]

The query:

```text
Q = "payment service unavailable"
```

becomes:

\[
Q=[1,1,1,0]
\]

The limitation is immediate: word order is lost.

```text
payment service unavailable
```

and:

```text
unavailable service payment
```

receive the same representation.

---

# 7. Term Frequency — TF

The first intuition is:

> A term appearing many times in a document may be important to that document.

Raw term frequency is:

\[
tf(t,d)=\text{count of term }t\text{ in document }d
\]

Example:

```text
D = "payment payment service"
```

gives:

\[
tf(payment,D)=2
\]

\[
tf(service,D)=1
\]

Raw TF is imperfect because relevance does not usually grow linearly with repetition.

A common alternative is logarithmic TF:

\[
tf_{log}(t,d)=
\begin{cases}
1+\log(tf(t,d)) & \text{if } tf(t,d)>0 \\
0 & \text{otherwise}
\end{cases}
\]

This reduces the influence of repeated occurrences.

---

# 8. Document Frequency — DF

Term frequency measures importance inside one document.

To know whether a term helps distinguish documents, we compute **document frequency**:

\[
df(t)=|\{d\in\mathcal{D}:t\in d\}|
\]

For:

```text
D1 = payment service
D2 = payment service unavailable
D3 = shipping service
```

we obtain:

| Term | df |
|---|---:|
| `payment` | 2 |
| `service` | 3 |
| `unavailable` | 1 |
| `shipping` | 1 |

`service` appears everywhere, so it is not very discriminative.

`unavailable` appears once, so it is much more informative.

---

# 9. Inverse Document Frequency — IDF

A simple IDF definition is:

\[
idf(t)=\log\left(\frac{N}{df(t)}\right)
\]

where:

- \(N\) = total number of documents;
- \(df(t)\) = number of documents containing term \(t\).

Here:

\[
N=3
\]

For `service`:

\[
idf(service)=\log(3/3)=0
\]

For `payment`:

\[
idf(payment)=\log(3/2)\approx0.405
\]

For `unavailable`:

\[
idf(unavailable)=\log(3)\approx1.099
\]

Thus:

```text
service       → low information
payment       → moderate information
unavailable   → high information
```

The key intuition is:

> Terms that are rare across the corpus are usually more useful for distinguishing documents.

Real systems often use smoothed IDF variants, but the principle is the same.

---

# 10. TF-IDF

TF-IDF combines local frequency and global rarity:

\[
tfidf(t,d)=tf(t,d)\times idf(t)
\]

For:

```text
D2 = "payment service unavailable"
```

using raw TF:

\[
D_2=[0.405,0,1.099,0]
\]

Similarly:

\[
D_1=[0.405,0,0,0]
\]

\[
D_3=[0,0,0,1.099]
\]

and:

\[
Q=[0.405,0,1.099,0]
\]

Documents and queries are now represented in the same vector space.

---

# 11. Vector Space Model

If the vocabulary contains \(M\) terms:

\[
V=\{t_1,t_2,\ldots,t_M\}
\]

each document is represented by:

\[
\vec d\in\mathbb{R}^M
\]

and the query by:

\[
\vec q\in\mathbb{R}^M
\]

Most dimensions are zero because a document contains only a small subset of the full vocabulary.

These are therefore **sparse vectors**.

---

# 12. Cosine Similarity

A standard similarity measure for TF-IDF vectors is cosine similarity:

\[
\cos(\vec q,\vec d)=
\frac{\vec q\cdot\vec d}
{\|\vec q\|\|\vec d\|}
\]

where:

\[
\vec q\cdot\vec d=\sum_i q_i d_i
\]

and:

\[
\|\vec d\|=\sqrt{\sum_i d_i^2}
\]

For non-negative TF-IDF vectors:

```text
cosine close to 1
→ similar direction / similar weighted term distribution

cosine close to 0
→ little or no useful overlap
```

## Why not use only the dot product?

A raw dot product is affected by vector magnitude.

Long documents may naturally contain more terms and therefore receive larger scores.

Cosine similarity normalizes both vectors and reduces the effect of raw document length.

---

# 13. Worked TF-IDF Example

Recall:

\[
Q=[0.405,0,1.099,0]
\]

\[
D_1=[0.405,0,0,0]
\]

\[
D_2=[0.405,0,1.099,0]
\]

\[
D_3=[0,0,0,1.099]
\]

Because \(D_2=Q\):

\[
\cos(Q,D_2)=1
\]

For \(D_1\):

\[
\cos(Q,D_1)\approx0.35
\]

For \(D_3\):

\[
\cos(Q,D_3)=0
\]

Ranking:

```text
1. D2    score ≈ 1.00
2. D1    score ≈ 0.35
3. D3    score = 0.00
```

This matches our intuition.

---

# 14. Inverted Index

A naive retriever could compare every query with every document.

This does not scale well.

An **inverted index** stores:

```text
term → documents containing that term
```

Example:

```text
payment
→ D1, D2

service
→ D1, D2, D3

unavailable
→ D2

shipping
→ D3
```

Each list is a **postings list**.

A posting can store more information:

```text
document ID
term frequency
term positions
field information
```

For example:

```text
payment
→ (D1, tf=1)
→ (D2, tf=1)
```

For query:

```text
payment unavailable
```

the search engine can inspect only the relevant postings instead of scanning the entire corpus.

---

# 15. Limitations of Raw TF-IDF

TF-IDF is an excellent baseline but has important limitations.

## Term-frequency growth

If `payment` occurs 50 times, raw TF gives far more weight than one occurrence, even though relevance usually does not increase linearly.

## Document length

Long documents naturally have more opportunities to contain query terms.

## Vocabulary mismatch

Consider:

```text
Query:
payment service unavailable

Document:
checkout cannot reach the billing backend
```

A human sees semantic similarity, but lexical overlap is small.

This is the **vocabulary mismatch problem**.

---

# 16. BM25

BM25 is a classical lexical ranking function that addresses important weaknesses of simpler TF-IDF schemes.

A common form is:

\[
BM25(D,Q)
=
\sum_{t\in Q}
IDF(t)
\cdot
\frac{
f(t,D)(k_1+1)
}{
f(t,D)
+
k_1
\left(
1-b+b\frac{|D|}{avgdl}
\right)
}
\]

where:

- \(f(t,D)\): frequency of term \(t\) in document \(D\);
- \(|D|\): document length;
- \(avgdl\): average document length;
- \(k_1\): controls term-frequency saturation;
- \(b\): controls document-length normalization.

Typical starting values are often around:

\[
k_1\in[1.2,2.0]
\]

and:

\[
b\approx0.75
\]

These are hyperparameters, not universal constants.

---

# 17. BM25 Term-Frequency Saturation

Raw TF grows linearly:

```text
1 occurrence   → 1
2 occurrences  → 2
10 occurrences → 10
```

BM25 grows more slowly.

Conceptually:

```text
score contribution
 ^
 |             ________
 |          __/
 |       __/
 |    __/
 |___/
 +--------------------------> term frequency
```

The first few occurrences provide strong evidence.

Additional repetitions provide progressively less new information.

This is **term-frequency saturation**.

---

# 18. BM25 Document-Length Normalization

The component:

\[
1-b+b\frac{|D|}{avgdl}
\]

adjusts the score according to document length.

If:

\[
|D|>avgdl
\]

the document receives a stronger normalization penalty.

The parameter \(b\) controls the effect:

\[
b=0
\]

means no length normalization.

\[
b=1
\]

means full normalization by relative document length.

---

# 19. A Common BM25 IDF Variant

A common BM25-style IDF is:

\[
IDF(t)
=
\log
\left(
1+
\frac{
N-df(t)+0.5
}{
df(t)+0.5
}
\right)
\]

This differs from the educational TF-IDF form:

\[
\log\left(\frac{N}{df(t)}\right)
\]

Libraries may use slightly different variants.

Therefore, two BM25 implementations may not return identical raw scores.

For evaluation, ranking quality matters more than comparing raw scores across implementations.

---

# 20. TF-IDF vs BM25

| Property | TF-IDF | BM25 |
|---|---|---|
| Lexical matching | Yes | Yes |
| Uses term rarity | Yes | Yes |
| TF saturation | Depends on TF variant | Explicit |
| Length normalization | Often cosine-based | Explicit |
| Semantic matching | No | No |
| Interpretability | High | High |
| Strong baseline | Yes | Yes, often stronger |

For RootLens:

```text
TF-IDF
→ educational baseline

BM25
→ main classical lexical baseline
```

---

# 21. Lexical Retrieval

TF-IDF and BM25 are **lexical retrieval** methods.

They work especially well when queries contain exact technical terms such as:

```text
PaymentService
UNAVAILABLE
rpc.response.status_code
HTTP 500
traceId
```

This is one reason lexical retrieval remains important even when neural embeddings are available.

---

# 22. Vocabulary Mismatch

The main weakness of lexical retrieval is that semantic similarity does not imply lexical overlap.

Example:

```text
Query:
payment service unavailable
```

Document:

```text
checkout cannot reach the billing backend
```

Possible semantic correspondences:

```text
payment       ↔ billing
service       ↔ backend
unavailable   ↔ cannot reach
```

BM25 does not inherently understand these relationships.

This motivates dense retrieval.

---

# 23. Sparse vs Dense Retrieval

## Sparse retrieval

Methods such as TF-IDF and BM25 use high-dimensional sparse representations.

Advantages:

- interpretable;
- efficient;
- excellent exact matching;
- strong for rare technical identifiers.

Main weakness:

- vocabulary mismatch.

## Dense retrieval

Embedding models map text to lower-dimensional dense vectors.

Example:

\[
[0.18,-0.04,0.71,\ldots]
\]

Dense retrieval can capture semantic similarity even without exact overlap.

This will be introduced only after the lexical baseline is evaluated.

---

# 24. Hybrid Retrieval

Lexical and dense retrieval have complementary strengths.

A future RootLens system may combine:

```text
BM25
+
dense retrieval
```

Example:

```text
Query:
PaymentService UNAVAILABLE
```

BM25 is likely strong because the terms are highly specific.

For:

```text
Query:
why can checkout no longer contact billing?
```

dense retrieval may better capture semantic equivalence.

Hybrid retrieval should only be introduced after lexical and dense systems have been measured independently.

---

# 25. Ranking

A retriever returns an ordered list:

\[
d_{(1)},d_{(2)},\ldots,d_{(k)}
\]

such that:

\[
score(q,d_{(1)})\ge score(q,d_{(2)})\ge\ldots
\]

Example:

```text
Query:
"gRPC service unavailable"

1. grpc-troubleshooting.md
2. payment-service.md
3. checkout-architecture.md
4. shipping-runbook.md
```

The question is not only whether a relevant document is retrieved, but also how high it appears.

---

# 26. Retrieval Evaluation

For each evaluation query, we define the documents considered relevant.

Example:

```text
Query:
"What does gRPC UNAVAILABLE mean?"

Relevant:
- grpc-troubleshooting.md
- grpc-status-codes.md
```

Suppose retrieval returns:

```text
1. grpc-troubleshooting.md
2. checkout-service.md
3. grpc-status-codes.md
4. payment-service.md
```

The ranking is compared with the known relevance judgments.

These judgments are often called **qrels**.

---

# 27. Precision@k

Precision measures how much of the retrieved set is relevant.

\[
Precision@k
=
\frac{
\text{relevant documents in top }k
}{
k
}
\]

Suppose the top five are:

```text
R, N, R, N, N
```

Then:

\[
Precision@5=\frac{2}{5}=0.4
\]

Precision asks:

> Of what I retrieved, how much is useful?

---

# 28. Recall@k

Recall measures how much of all relevant information was retrieved.

\[
Recall@k
=
\frac{
\text{relevant documents in top }k
}{
\text{total relevant documents}
}
\]

Suppose there are four relevant documents in the corpus and the top five contain two.

Then:

\[
Recall@5=\frac{2}{4}=0.5
\]

Recall asks:

> Of everything useful, how much did I find?

---

# 29. Why Recall Matters in RAG

Suppose the LLM needs one specific document to answer correctly.

If retrieval misses it:

```text
relevant evidence
      X
retriever
      ↓
LLM
```

the model cannot reliably use evidence it never received.

Therefore:

> Retrieval recall limits the grounded evidence available to generation.

For RootLens, if the documentation explaining `UNAVAILABLE` is not retrieved, better prompting cannot compensate for missing evidence.

---

# 30. Mean Reciprocal Rank — MRR

When the first relevant result matters, we can use reciprocal rank:

\[
RR(q)=\frac{1}{\text{rank of first relevant document}}
\]

Examples:

```text
first relevant at rank 1 → RR = 1
first relevant at rank 2 → RR = 1/2
first relevant at rank 5 → RR = 1/5
```

Across queries:

\[
MRR
=
\frac{1}{n}
\sum_{i=1}^{n}RR(q_i)
\]

MRR rewards systems that place at least one useful result very early.

---

# 31. nDCG — Preview

Precision and recall usually use binary relevance:

```text
relevant
not relevant
```

Sometimes relevance is graded:

```text
3 = highly relevant
2 = relevant
1 = marginally relevant
0 = irrelevant
```

nDCG rewards highly relevant documents appearing near the top while discounting useful documents that appear lower.

We do not need nDCG for the first RootLens benchmark if relevance remains binary.

---

# 32. Evaluation Dataset

A RootLens retrieval example could be:

```json
{
  "query_id": "q1",
  "query": "What can cause a gRPC service to return UNAVAILABLE?",
  "relevant_documents": [
    "grpc-troubleshooting.md"
  ]
}
```

Another:

```json
{
  "query_id": "q2",
  "query": "How does Checkout call PaymentService?",
  "relevant_documents": [
    "checkout-architecture.md",
    "payment-service.md"
  ]
}
```

The same benchmark should be reused to compare:

```text
TF-IDF
BM25
dense retrieval
hybrid retrieval
reranking
```

---

# 33. Ground Truth and Data Leakage

Evaluation information must remain separate from the knowledge available to the retriever.

Recommended structure:

```text
data/
├── knowledge/
│   └── documents available to RootLens
│
└── evaluation/
    └── relevance judgments / hidden ground truth
```

If evaluating:

```text
paymentUnreachable
```

and the searchable knowledge contains an explicit description of that injected fault and its exact consequence, the benchmark may measure answer lookup rather than investigation.

---

# 34. Chunking — Preview

Long files are often divided into smaller retrievable units.

```text
runbook.md
├── chunk 1
├── chunk 2
├── chunk 3
└── ...
```

Small chunks:

```text
+ precise
+ less irrelevant context
- may lose surrounding meaning
```

Large chunks:

```text
+ preserve context
- contain more noise
- consume more context window
```

Chunking is therefore another parameter to evaluate rather than an arbitrary implementation detail.

For the first RootLens lexical benchmark, documents can remain small enough that chunking is not yet necessary.

---

# 35. Metadata Filtering — Preview

Operational documents naturally have metadata:

```json
{
  "service": "checkout",
  "type": "runbook",
  "version": "3.1.0",
  "environment": "production"
}
```

Retrieval can combine filters and ranking:

```text
filter:
service = checkout

then rank:
BM25(query, document)
```

RootLens will likely benefit from metadata such as:

- service;
- component;
- source;
- version;
- document type;
- environment;
- incident date.

---

# 36. RootLens Retrieval Roadmap

The intended progression is:

```text
Baseline 0
exact keyword matching
        ↓
Baseline 1
TF-IDF + cosine similarity
        ↓
Baseline 2
BM25
        ↓
Baseline 3
dense embeddings
        ↓
Baseline 4
hybrid lexical + dense
        ↓
Baseline 5
reranking
```

Every new layer should answer:

1. What limitation are we solving?
2. What simpler baseline are we comparing against?
3. Which metric should improve?
4. Did it actually improve?
5. What cost or complexity did we add?

---

# 37. Why Start Without a Vector Database?

A vector database solves problems such as:

- storing embeddings;
- nearest-neighbor search;
- metadata filtering;
- persistence;
- scalable indexing.

The first RootLens corpus will be tiny.

Using a vector database immediately would hide retrieval mechanics behind unnecessary infrastructure.

For the first experiments:

```text
Python
+
small in-memory corpus
```

is enough.

---

# 38. Why Start Without an LLM?

If we immediately build:

```text
query
→ retriever
→ LLM
→ answer
```

and the answer is poor, the failure could come from:

- tokenization;
- missing documents;
- retrieval;
- ranking;
- chunking;
- context formatting;
- model reasoning;
- hallucination.

Instead:

```text
Phase 1:
query → ranked documents

Phase 2:
query → ranked documents → answer
```

This keeps experiments interpretable.

---

# 39. RootLens-Specific Retrieval Challenges

## Exact technical identifiers

Examples:

```text
PaymentService
PlaceOrder
UNAVAILABLE
DEADLINE_EXCEEDED
rpc.response.status_code
```

Lexical retrieval is likely to perform well.

## Synonyms and conceptual language

Examples:

```text
payment ↔ billing
service unavailable ↔ cannot reach backend
latency spike ↔ slow downstream dependency
```

Dense retrieval may help.

## Version-sensitive documentation

Service behaviour may change across versions.

Metadata and temporal context may become important.

## Incident language vs documentation language

An incident may say:

```text
checkout could not resolve payment
```

while documentation says:

```text
name resolution failure
```

Hybrid retrieval may later help bridge these formulations.

## Evidence leakage

Historical incidents are useful knowledge but may leak benchmark answers.

Evaluation must control what RootLens is allowed to retrieve.

---

# 40. Key Equations

## Term frequency

\[
tf(t,d)=count(t,d)
\]

## Document frequency

\[
df(t)=|\{d:t\in d\}|
\]

## Simple IDF

\[
idf(t)=\log\left(\frac{N}{df(t)}\right)
\]

## TF-IDF

\[
tfidf(t,d)=tf(t,d)\cdot idf(t)
\]

## Cosine similarity

\[
\cos(q,d)
=
\frac{q\cdot d}
{\|q\|\|d\|}
\]

## BM25

\[
BM25(D,Q)
=
\sum_{t\in Q}
IDF(t)
\frac{
f(t,D)(k_1+1)
}{
f(t,D)
+
k_1
\left(
1-b+b\frac{|D|}{avgdl}
\right)
}
\]

## Precision@k

\[
Precision@k
=
\frac{
\#\text{ relevant documents in top }k
}{
k
}
\]

## Recall@k

\[
Recall@k
=
\frac{
\#\text{ relevant documents in top }k
}{
\#\text{ relevant documents}
}
\]

## Reciprocal Rank

\[
RR(q)
=
\frac{1}{
\text{rank of first relevant result}
}
\]

## Mean Reciprocal Rank

\[
MRR
=
\frac{1}{|Q|}
\sum_{q\in Q}RR(q)
\]

---

# 41. Interview Questions

## Why do we need IDF?

Because a term appearing in almost every document carries little discriminative information. IDF increases the weight of relatively rare terms.

## Why not use raw TF alone?

Because repeated occurrences do not imply linearly increasing relevance. BM25 explicitly models term-frequency saturation.

## Why cosine similarity for TF-IDF?

Because it normalizes vector magnitude and therefore reduces the tendency of longer documents to score higher purely because they contain more terms.

## What is an inverted index?

A mapping:

```text
term → documents containing the term
```

It avoids scanning the entire corpus for every query.

## What is the main weakness of BM25?

It relies primarily on lexical overlap and does not inherently understand semantic equivalence such as `billing` and `payment`.

## Why is BM25 still useful when embeddings exist?

Because it is efficient, interpretable, and especially strong for exact technical identifiers, rare terms, error codes, API names, and service names.

## Precision vs recall?

Precision asks:

> Of what I retrieved, how much is relevant?

Recall asks:

> Of everything relevant, how much did I retrieve?

## Why is recall especially important in RAG?

Because evidence that is not retrieved cannot be reliably used by the LLM.

## What does MRR measure?

How high the first relevant result appears.

## Sparse vs dense retrieval?

Sparse retrieval uses explicit vocabulary dimensions and primarily captures lexical overlap. Dense retrieval uses learned numerical embeddings and can capture semantic similarity.

## Why hybrid retrieval?

Because lexical and semantic methods have complementary strengths.

---

# 42. What We Will Implement Ourselves

Before using high-level libraries, the first RootLens retriever should implement:

```text
tokenize()
term_frequency()
document_frequency()
inverse_document_frequency()
tfidf_vector()
cosine_similarity()
rank_documents()
```

Then:

```text
BM25Retriever
```

The purpose is educational. Later we can replace components with mature libraries while still understanding the abstractions.

---

# 43. Milestone 1 Definition of Done

The Information Retrieval milestone is complete when:

- [ ] a small RootLens knowledge corpus exists;
- [ ] evaluation ground truth is separate;
- [ ] tokenization is implemented and tested;
- [ ] TF-IDF retrieval is implemented;
- [ ] cosine ranking is implemented;
- [ ] BM25 retrieval is implemented;
- [ ] a small query/relevance benchmark exists;
- [ ] Precision@k is measured;
- [ ] Recall@k is measured;
- [ ] MRR is measured;
- [ ] retrieval failures are analyzed;
- [ ] BM25 is compared with simpler baselines;
- [ ] results are documented.

No LLM is required for this milestone.

---

# 44. Main Takeaways

```text
Information Retrieval
=
finding and ranking information relevant to a query
```

```text
TF
=
importance of a term inside a document
```

```text
IDF
=
how discriminative a term is across the corpus
```

```text
TF-IDF
=
local importance × global rarity
```

```text
Cosine similarity
=
normalized vector similarity
```

```text
Inverted index
=
efficient term → document lookup
```

```text
BM25
=
lexical ranking with TF saturation
and document-length normalization
```

```text
Recall
=
did we retrieve the information that matters?
```

```text
MRR
=
how early did the first relevant result appear?
```

For RootLens:

> Build the simplest measurable retriever first, understand its failure modes, and only then add embeddings, hybrid retrieval, reranking and generation.

---

# 45. References

## Core textbook

Christopher D. Manning, Prabhakar Raghavan, and Hinrich Schütze.  
**Introduction to Information Retrieval.** Cambridge University Press, 2008.

Free online edition:

https://nlp.stanford.edu/IR-book/

Particularly relevant chapters:

- Chapter 1 — Boolean retrieval
- Chapter 2 — The term vocabulary and postings lists
- Chapter 6 — Scoring, term weighting and the vector space model
- Chapter 7 — Computing scores in a complete search system
- Chapter 8 — Evaluation in information retrieval
- Chapter 11 — Probabilistic information retrieval

## BM25

Stephen Robertson and Hugo Zaragoza.  
**The Probabilistic Relevance Framework: BM25 and Beyond.**  
Foundations and Trends in Information Retrieval, 3(4), 2009.

https://doi.org/10.1561/1500000019

## Stanford course

Stanford CS276 — Information Retrieval and Web Search:

https://web.stanford.edu/class/cs276/

---

# 46. Next Step

The next implementation step is intentionally small:

```python
def tokenize(text: str) -> list[str]:
    ...
```

followed by:

```python
def term_frequency(tokens: list[str]) -> dict[str, int]:
    ...
```

with unit tests.

Then we will progress through:

```text
DF
↓
IDF
↓
TF-IDF vectors
↓
cosine similarity
↓
document ranking
↓
BM25
↓
offline retrieval evaluation
```
