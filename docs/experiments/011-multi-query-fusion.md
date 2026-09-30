# Experiment 011 — Multi-Query Fusion Strategies

## Status

Completed on the DEV split only.

The frozen TEST split was not used.

---

# Objective

Evaluate whether simple deterministic fusion strategies can exploit the high-recall candidate pool produced by Experiment 010 better than Reciprocal Rank Fusion (RRF).

Experiment 010 showed:

```text
Dense candidate recall       = 0.9236
Multi-query union recall     = 0.9896

Dense oracle Recall@3        = 0.9236
Union oracle Recall@3        = 0.9583

Dense oracle nDCG@3          = 0.9877
Union oracle nDCG@3          = 1.0000
```

However, RRF failed to preserve most newly recovered relevant documents.

Experiment 011 therefore holds the candidate pool fixed and changes only the fusion rule.

---

# Experimental Setup

```text
corpus                  = Benchmark v2
documents               = 24
DEV queries             = 24
retrieval unit          = whole document

dense retriever         = BAAI/bge-small-en-v1.5
rewrite model           = qwen-3.6-35b-instruct
rewrites/query          = 3
original query retained = yes

candidates/query        = 10
candidate union         = fixed
```

Frozen rewrites:

```text
data/benchmark_v2/dev_rewrites_v1.json
```

The benchmark makes no LLM calls.

The TEST split remains frozen.

---

# Fusion Strategies

## Dense Baseline

Use the original query only.

---

## Reciprocal Rank Fusion

For document \(d\):

\[
RRF(d) = \sum_i \frac{1}{k + rank_i(d)}
\]

RRF uses rank position only.

---

## MaxSim

For every candidate document \(d\):

\[
MaxSim(d) = \max_i sim(q_i, d)
\]

where \(q_i\) includes the original query and all frozen rewrites.

Intuition:

> A document should survive if it is strongly relevant to at least one formulation of the information need.

---

## MeanSim

\[
MeanSim(d) = \frac{1}{m}\sum_i sim(q_i,d)
\]

Intuition:

> A document should rank highly if it is consistently relevant across query formulations.

For MaxSim and MeanSim, every document in the union is explicitly scored against every expanded query. Absence from a top-10 ranking is not treated as a zero similarity.

---

# Aggregate Results

| Metric | Dense | RRF | MaxSim | MeanSim |
|---|---:|---:|---:|---:|
| Precision@1 | **0.9167** | **0.9167** | **0.9167** | **0.9167** |
| Recall@1 | 0.3507 | 0.3472 | **0.3542** | 0.3507 |
| Recall@3 | **0.7500** | 0.7326 | 0.7049 | 0.7257 |
| Recall@5 | **0.8299** | 0.8194 | **0.8299** | 0.8125 |
| Recall@10 | 0.9236 | **0.9340** | **0.9340** | **0.9340** |
| MRR@3 | **0.9583** | **0.9583** | **0.9583** | **0.9583** |
| nDCG@3 | 0.8317 | **0.8394** | 0.8177 | 0.8316 |
| nDCG@5 | 0.8500 | **0.8602** | 0.8493 | 0.8455 |

---

# Delta vs Dense

## RRF

```text
Precision@1: +0.0000
Recall@1:    -0.0035
Recall@3:    -0.0174
Recall@5:    -0.0104
Recall@10:   +0.0104
MRR@3:       +0.0000
nDCG@3:      +0.0076
nDCG@5:      +0.0102
```

RRF slightly improves graded ranking quality and Recall@10, but decreases top-3 and top-5 evidence recall.

---

## MaxSim

```text
Precision@1: +0.0000
Recall@1:    +0.0035
Recall@3:    -0.0451
Recall@5:    +0.0000
Recall@10:   +0.0104
MRR@3:       +0.0000
nDCG@3:      -0.0141
nDCG@5:      -0.0008
```

MaxSim does not validate the hypothesis that one strong query-document match is sufficient to preserve complementary evidence.

---

## MeanSim

```text
Precision@1: +0.0000
Recall@1:    +0.0000
Recall@3:    -0.0243
Recall@5:    -0.0174
Recall@10:   +0.0104
MRR@3:       +0.0000
nDCG@3:      -0.0001
nDCG@5:      -0.0045
```

MeanSim is close to Dense on graded ranking but still loses evidence recall.

---

# Category-Level Results

## Architecture

```text
Dense    R@3=0.7500  R@5=1.0000  R@10=1.0000  nDCG@3=0.8414
RRF      R@3=0.8333  R@5=1.0000  R@10=1.0000  nDCG@3=0.8716
MaxSim   R@3=0.8333  R@5=0.9167  R@10=1.0000  nDCG@3=0.9186
MeanSim  R@3=0.8333  R@5=1.0000  R@10=1.0000  nDCG@3=0.8716
```

All multi-query fusion methods improve top-3 architecture retrieval.

---

## Exact Identifier

```text
Dense    R@3=0.9167  R@5=0.9167  R@10=1.0000  nDCG@3=0.9607
RRF      R@3=0.9167  R@5=0.9167  R@10=1.0000  nDCG@3=0.9607
MaxSim   R@3=0.7917  R@5=0.9167  R@10=1.0000  nDCG@3=0.9263
MeanSim  R@3=0.7917  R@5=0.9167  R@10=1.0000  nDCG@3=0.9263
```

Dense and RRF best preserve exact-identifier behavior.

---

## Hard Negative

```text
Dense    R@3=0.7500  R@5=0.7500  R@10=0.7500  nDCG@3=0.8951
RRF      R@3=0.7500  R@5=0.7500  R@10=1.0000  nDCG@3=0.8951
MaxSim   R@3=0.7500  R@5=0.7500  R@10=0.7500  nDCG@3=0.8951
MeanSim  R@3=0.7500  R@5=0.7500  R@10=1.0000  nDCG@3=0.8951
```

RRF and MeanSim improve candidate coverage without changing top-3 graded quality.

---

## Multi-Document

```text
Dense    R@3=0.5000  R@5=0.5833  R@10=0.7500  nDCG@3=0.7885
RRF      R@3=0.4167  R@5=0.5000  R@10=0.6667  nDCG@3=0.8469
MaxSim   R@3=0.4167  R@5=0.5833  R@10=0.8333  nDCG@3=0.6649
MeanSim  R@3=0.4167  R@5=0.5000  R@10=0.6667  nDCG@3=0.7576
```

No simple fusion strategy solves the multi-document evidence-selection problem.

---

## Observability

```text
Dense    R@3=0.8889  R@5=1.0000  R@10=1.0000  nDCG@3=0.6839
RRF      R@3=0.7222  R@5=0.8889  R@10=1.0000  nDCG@3=0.5375
MaxSim   R@3=0.7222  R@5=0.8333  R@10=1.0000  nDCG@3=0.6374
MeanSim  R@3=0.7222  R@5=0.8333  R@10=1.0000  nDCG@3=0.6269
```

Dense remains clearly strongest for observability queries.

---

## Semantic Paraphrase

```text
Dense    R@3=0.6250  R@5=0.6250  R@10=0.9167  nDCG@3=0.8203
RRF      R@3=0.7083  R@5=0.7083  R@10=0.9167  nDCG@3=0.8584
MaxSim   R@3=0.6667  R@5=0.8333  R@10=0.9167  nDCG@3=0.8691
MeanSim  R@3=0.7083  R@5=0.7083  R@10=0.9167  nDCG@3=0.8505
```

Multi-query fusion is useful for semantic-paraphrase queries.

---

## Troubleshooting

```text
Dense    R@3=0.7917  R@5=0.8750  R@10=0.9375  nDCG@3=0.8163
RRF      R@3=0.7083  R@5=0.8750  R@10=0.9375  nDCG@3=0.8595
MaxSim   R@3=0.7083  R@5=0.8750  R@10=0.9375  nDCG@3=0.7678
MeanSim  R@3=0.7917  R@5=0.8750  R@10=0.9375  nDCG@3=0.8555
```

RRF and MeanSim improve graded ranking in troubleshooting, but neither improves evidence recall.

---

# Recovered Evidence Retention

Experiment 010 recovered five previously missing relevant documents into the union candidate pool.

Experiment 011 tests whether the different fusion strategies preserve them.

## dev-008

```text
incident-response-guide.md
```

Final rank:

```text
RRF      = outside top 10
MaxSim   = outside top 10
MeanSim  = outside top 10
```

---

## dev-015

```text
grpc-troubleshooting.md
```

Final rank:

```text
RRF      = outside top 10
MaxSim   = outside top 10
MeanSim  = outside top 10
```

---

## dev-020

```text
grpc-troubleshooting.md
```

Final rank:

```text
RRF      = outside top 10
MaxSim   = 9
MeanSim  = outside top 10
```

---

## dev-022

```text
metrics-guide.md
```

Final rank:

```text
RRF      = outside top 10
MaxSim   = outside top 10
MeanSim  = outside top 10
```

---

## dev-023

```text
metrics-guide.md
```

Final rank:

```text
RRF      = 9
MaxSim   = outside top 10
MeanSim  = 9
```

---

# Retention Summary

```text
Recovered documents = 5
```

| Fusion | Top 3 | Top 5 | Top 10 |
|---|---:|---:|---:|
| RRF | 0/5 | 0/5 | 1/5 |
| MaxSim | 0/5 | 0/5 | 1/5 |
| MeanSim | 0/5 | 0/5 | 1/5 |

No simple pointwise fusion strategy reliably preserves the complementary evidence recovered by multi-query candidate generation.

---

# Interpretation

Experiment 011 rejects the hypothesis that the Experiment 010 bottleneck is specific to RRF.

Three distinct fusion philosophies were tested:

```text
RRF
→ consensus in rank positions

MaxSim
→ strongest semantic match to any query

MeanSim
→ average semantic relevance across queries
```

All three fail to preserve most newly recovered evidence.

Therefore the problem is broader than choosing a better scalar aggregation rule.

The candidate union contains the evidence, but relevant complementary documents often have lower pointwise relevance than other candidates.

This suggests that the final evidence-selection problem is a **set-selection problem**, not only a document-scoring problem.

A useful RootLens evidence set should optimize properties such as:

```text
relevance
+
coverage
+
complementarity
+
non-redundancy
```

rather than independently maximizing one scalar score per document.

---

# Architecture Decision

Do not adopt RRF, MaxSim, or MeanSim as the default multi-query fusion strategy.

The default retrieval baseline remains:

```text
Query
  ↓
BAAI/bge-small-en-v1.5
  ↓
whole-document dense retrieval
  ↓
top-k evidence
```

Retain multi-query retrieval as a high-recall candidate-generation capability.

Do not discard the union candidate pool:

```text
candidate recall = 0.9896
```

The candidate-generation stage is strong.

The next architectural problem is explicit evidence-set selection.

---

# Next Research Question

The next question is:

> Can a set-aware selector choose complementary evidence from the high-recall multi-query union better than independent document scoring?

A natural next baseline is Maximal Marginal Relevance (MMR), which balances query relevance and redundancy with already selected documents.

More directly aligned with the multi-query setup, a query-coverage objective can greedily select documents that improve coverage across the expanded query representations.

These approaches should be evaluated before introducing learned selection or additional LLM reasoning.

---

# Experiment 012 Direction

## Set-Aware Evidence Selection

Keep fixed:

```text
Dense model           = BAAI/bge-small-en-v1.5
frozen rewrites       = dev_rewrites_v1.json
rewrites/query        = 3
candidates/query      = 10
candidate union       = unchanged
benchmark             = DEV only
```

Compare:

```text
Dense baseline
RRF baseline
MMR
query-coverage selection
```

The key diagnostic should remain recovered-evidence retention:

```text
top 3
top 5
top 10
```

If set-aware selection still cannot exploit the union candidate pool, the next step should be query decomposition so that complementary evidence requirements are represented explicitly as retrieval subgoals.

---

# Final Conclusion

Experiment 011 shows that simple scalar fusion is not sufficient.

RRF remains the strongest of the three multi-query fusion rules on aggregate nDCG:

```text
nDCG@3:
Dense    0.8317
RRF      0.8394
MaxSim   0.8177
MeanSim  0.8316
```

but Dense remains strongest on Recall@3:

```text
Dense    0.7500
RRF      0.7326
MaxSim   0.7049
MeanSim  0.7257
```

Most importantly, every tested fusion strategy preserves only:

```text
1 / 5
```

newly recovered relevant documents in its top 10.

Therefore:

```text
candidate generation is no longer the main bottleneck
simple fusion is not enough
evidence selection must become set-aware
```

The frozen TEST split remains untouched.
