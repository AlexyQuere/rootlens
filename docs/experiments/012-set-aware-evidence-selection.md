# Experiment 012 — Set-Aware Evidence Selection

## Status

Completed on the DEV split only. The frozen TEST split was not used.

## Objective

Evaluate whether set-aware evidence selection can exploit the high-recall multi-query candidate pool better than scalar document fusion.

Experiment 010 established:

```text
Dense candidate recall   = 0.9236
Multi-query union recall = 0.9896
```

Experiment 011 showed that RRF, MaxSim and MeanSim retained only 1/5 newly recovered relevant documents in their top 10.

Experiment 012 compares:
- Dense
- RRF
- Maximal Marginal Relevance (MMR)
- Greedy Query Coverage

Controls remain fixed:
```text
documents               = 24
DEV queries             = 24
dense model             = BAAI/bge-small-en-v1.5
rewrite model           = qwen-3.6-35b-instruct
rewrites/query          = 3
candidates/query        = 10
MMR lambda              = 0.5
candidate union         = fixed
```

## Aggregate Results

| Metric | Dense | RRF | MMR | Coverage |
|---|---:|---:|---:|---:|
| Precision@1 | 0.9167 | 0.9167 | 0.8750 | 0.9167 |
| Recall@1 | 0.3507 | 0.3472 | 0.3368 | 0.3507 |
| Recall@3 | **0.7500** | 0.7326 | 0.6840 | 0.6979 |
| Recall@5 | **0.8299** | 0.8194 | 0.8160 | 0.8090 |
| Recall@10 | 0.9236 | **0.9340** | 0.9201 | 0.9201 |
| MRR@3 | 0.9583 | 0.9583 | 0.9375 | 0.9583 |
| nDCG@3 | 0.8317 | **0.8394** | 0.7984 | 0.8056 |
| nDCG@5 | 0.8500 | **0.8602** | 0.8240 | 0.8258 |

## Recovered-Evidence Retention

Five previously missing relevant documents were available in the multi-query union.

```text
RRF       top3=0/5  top5=0/5  top10=1/5
MMR       top3=0/5  top5=0/5  top10=1/5
Coverage  top3=0/5  top5=0/5  top10=1/5
```

The known failure `dev-021` still does not recover `distributed-tracing-guide.md` at candidate-generation time.

## Mechanism Diagnostics

### Query Coverage@5

```text
Dense     = 0.9957
RRF       = 0.9943
MMR       = 1.0000
Coverage  = 1.0000
```

### Mean Pairwise Similarity@5

```text
Dense     = 0.7600
RRF       = 0.7625
MMR       = 0.7522
Coverage  = 0.7618
```

MMR behaves as intended at the mechanism level: it produces a slightly less redundant set.

Query Coverage also behaves as intended: it saturates its own coverage objective.

However, neither mechanism improvement translates into better retrieval quality.

## Key Interpretation

The crucial result is:

```text
Dense Query Coverage@5 = 0.9957
```

The semantic rewrites are already almost completely covered by the Dense top-5.

Therefore the four query representations are not acting as distinct evidence requirements. They are mostly paraphrases of the same information need.

This explains why a selector can reach almost perfect query-coverage while still failing to retain complementary evidence.

The problem is now the representation of the information need, not the selection rule.

## Architecture Decision

Stop tuning:
- MMR lambda
- coverage weights
- candidate_k
- additional scalar or set-aware selectors

on the current paraphrase-based query representation.

Keep:
- Dense BGE as the default retrieval baseline
- semantic multi-query as a useful high-recall candidate generator

Move next to explicit query decomposition.

## Next Experiment — Query Decomposition

Instead of:

```text
q
→ paraphrase 1
→ paraphrase 2
→ paraphrase 3
```

generate distinct evidence subgoals:

```text
complex incident question
        ↓
metrics subquery
trace subquery
logs subquery
runbook / architecture subquery
```

Example:

```text
How should I investigate a sudden checkout error-rate increase
from detection to request-level evidence?
```

should become something like:

```text
1. Which metric detects and quantifies the checkout error-rate increase?
2. Which trace evidence localizes the failing downstream component?
3. Which logs correlate request-level failures with the trace?
4. Which incident-response guidance connects detection to RCA?
```

Experiment 013 should compare:
- Dense original query
- semantic multi-query
- decomposed multi-query

Primary metrics:
- candidate recall
- Recall@3 / Recall@5
- nDCG@3
- multi-document category performance
- recovered-evidence coverage
- query-representation diversity

## Final Conclusion

Experiment 012 rejects the hypothesis that set-aware selection alone can solve the evidence-selection bottleneck.

```text
candidate generation      → strong
scalar fusion             → insufficient
set-aware selection       → insufficient
semantic query facets     → too redundant
```

The next architectural change should therefore be **query decomposition**.

The frozen TEST split remains untouched.
