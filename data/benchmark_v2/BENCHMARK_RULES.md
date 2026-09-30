# RootLens Retrieval Benchmark v2 — Evaluation Rules

## Dataset

- Knowledge documents: 24
- DEV queries: 24
- TEST queries: 16
- Total queries: 40

## Graded relevance

- `2`: directly relevant / primary answer source
- `1`: supporting or partially relevant
- `0`: not relevant (implicit when absent from `relevance`)

Binary metrics such as Recall and MRR treat every grade greater than zero as relevant.

Graded metrics such as nDCG preserve the distinction between grade 1 and grade 2.

## DEV / TEST policy

Use DEV for:
- retrieval architecture choices;
- chunking experiments;
- embedding-model comparisons;
- reranking experiments;
- fusion choices;
- parameter tuning;
- failure analysis.

TEST is frozen.

Do not select a method because it improves TEST. TEST should be evaluated only at explicit milestone checkpoints.

## Benchmark integrity

Before evaluation:
- every document must be non-empty;
- every query ID must be unique;
- every qrel document must exist in the corpus;
- relevance grades must be 1 or 2;
- DEV and TEST must not share identical IDs or identical query text.

## Primary metrics

- Precision@1
- Recall@1
- Recall@3
- Recall@5
- MRR@3
- nDCG@3
- nDCG@5

## Reporting

Always report:
1. aggregate metrics;
2. metrics by query category;
3. the main success cases;
4. the main failure cases;
5. any architecture regression.

Do not modify corpus text or qrels merely to improve a retriever's score.
