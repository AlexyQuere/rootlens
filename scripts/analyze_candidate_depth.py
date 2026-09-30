import json
from collections import defaultdict
from pathlib import Path

from rootlens.evaluation.benchmark import (
    validate_benchmark,
)
from rootlens.evaluation.retrieval_metrics import (
    ndcg_at_k,
    oracle_ndcg_at_k_from_candidates,
    oracle_recall_at_k_from_candidates,
    recall_at_k,
)
from rootlens.retrieval.dense_retriever import (
    BGEEncoder,
    DenseRetriever,
)


ROOT = Path(__file__).resolve().parents[1]

BENCHMARK_DIR = (
    ROOT
    / "data"
    / "benchmark_v2"
)

KNOWLEDGE_DIR = (
    BENCHMARK_DIR
    / "knowledge"
)

DEV_FILE = (
    BENCHMARK_DIR
    / "dev_queries.json"
)


DEPTHS = (
    1,
    3,
    5,
    10,
    20,
)

ORACLE_DEPTHS = (
    5,
    10,
    20,
)


def load_documents() -> dict[str, str]:
    documents = {}

    for path in sorted(
        KNOWLEDGE_DIR.glob("*.md")
    ):
        content = path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            raise ValueError(
                f"Empty document: "
                f"{path.name}"
            )

        documents[path.name] = content

    return documents


def load_queries() -> list[dict]:
    return json.loads(
        DEV_FILE.read_text(
            encoding="utf-8"
        )
    )


def mean(
    values: list[float],
) -> float:
    if not values:
        return 0.0

    return sum(values) / len(values)


def maximum_recall_at_k(
    relevant: set[str],
    k: int,
) -> float:
    if not relevant:
        return 0.0

    return (
        min(
            k,
            len(relevant),
        )
        / len(relevant)
    )


def main() -> None:
    documents = load_documents()
    queries = load_queries()

    validate_benchmark(
        documents,
        queries,
    )

    print(
        "Experiment 007 — "
        "Candidate Recall and "
        "Reranking Readiness"
    )

    print(
        f"DEV only | "
        f"documents={len(documents)} "
        f"| queries={len(queries)}"
    )

    retriever = DenseRetriever(
        documents,
        encoder=BGEEncoder(),
    )

    aggregate_recall = {
        depth: []
        for depth in DEPTHS
    }

    aggregate_oracle_recall = {
        depth: []
        for depth in ORACLE_DEPTHS
    }

    aggregate_oracle_ndcg = {
        depth: []
        for depth in ORACLE_DEPTHS
    }

    actual_recall_3 = []
    actual_ndcg_3 = []

    by_category = defaultdict(
        lambda: {
            "recall3": [],
            "recall10": [],
            "oracle3_from10": [],
        }
    )

    candidate_failures_10 = []
    reranking_opportunities_10 = []

    max_depth = max(
        DEPTHS
    )

    for example in queries:
        results = retriever.search(
            example["query"],
            k=max_depth,
        )

        retrieved = [
            document_id
            for document_id, _
            in results
        ]

        relevance = (
            example["relevance"]
        )

        relevant = {
            document_id
            for document_id, grade
            in relevance.items()
            if grade > 0
        }

        for depth in DEPTHS:
            value = recall_at_k(
                retrieved,
                relevant,
                k=depth,
            )

            aggregate_recall[
                depth
            ].append(value)

        r3 = recall_at_k(
            retrieved,
            relevant,
            k=3,
        )

        ndcg3 = ndcg_at_k(
            retrieved,
            relevance,
            k=3,
        )

        actual_recall_3.append(
            r3
        )

        actual_ndcg_3.append(
            ndcg3
        )

        for depth in ORACLE_DEPTHS:
            candidates = (
                retrieved[:depth]
            )

            oracle_recall = (
                oracle_recall_at_k_from_candidates(
                    candidates,
                    relevant,
                    k=3,
                )
            )

            oracle_ndcg = (
                oracle_ndcg_at_k_from_candidates(
                    candidates,
                    relevance,
                    k=3,
                )
            )

            aggregate_oracle_recall[
                depth
            ].append(
                oracle_recall
            )

            aggregate_oracle_ndcg[
                depth
            ].append(
                oracle_ndcg
            )

        category = (
            example["category"]
        )

        r10 = recall_at_k(
            retrieved,
            relevant,
            k=10,
        )

        oracle_3_from_10 = (
            oracle_recall_at_k_from_candidates(
                retrieved[:10],
                relevant,
                k=3,
            )
        )

        by_category[
            category
        ][
            "recall3"
        ].append(r3)

        by_category[
            category
        ][
            "recall10"
        ].append(r10)

        by_category[
            category
        ][
            "oracle3_from10"
        ].append(
            oracle_3_from_10
        )

        max_recall_10 = (
            maximum_recall_at_k(
                relevant,
                k=10,
            )
        )

        if (
            r10
            < max_recall_10 - 1e-12
        ):
            missing = sorted(
                relevant
                - set(
                    retrieved[:10]
                )
            )

            candidate_failures_10.append(
                (
                    example[
                        "query_id"
                    ],
                    r10,
                    missing,
                )
            )

        if (
            oracle_3_from_10
            > r3 + 1e-12
        ):
            reranking_opportunities_10.append(
                (
                    example[
                        "query_id"
                    ],
                    r3,
                    oracle_3_from_10,
                )
            )

    print()
    print(
        "=== Candidate Recall ==="
    )

    for depth in DEPTHS:
        print(
            f"Recall@{depth}: "
            f"{mean(aggregate_recall[depth]):.4f}"
        )

    print()
    print(
        "=== Reranking Upper Bound ==="
    )

    print(
        "Actual Recall@3: "
        f"{mean(actual_recall_3):.4f}"
    )

    print(
        "Actual nDCG@3: "
        f"{mean(actual_ndcg_3):.4f}"
    )

    for depth in ORACLE_DEPTHS:
        print()
        print(
            f"Candidates top-{depth}"
        )

        print(
            "  Oracle Recall@3: "
            f"{mean(aggregate_oracle_recall[depth]):.4f}"
        )

        print(
            "  Oracle nDCG@3: "
            f"{mean(aggregate_oracle_ndcg[depth]):.4f}"
        )

    print()
    print(
        "=== By Category ==="
    )

    for category in sorted(
        by_category
    ):
        values = (
            by_category[
                category
            ]
        )

        print(
            f"{category}: "
            f"R@3="
            f'{mean(values["recall3"]):.4f} '
            f"R@10="
            f'{mean(values["recall10"]):.4f} '
            f"OracleR@3(top10)="
            f'{mean(values["oracle3_from10"]):.4f}'
        )

    print()
    print(
        "=== Candidate-generation "
        "failures at top 10 ==="
    )

    print(
        f"Count: "
        f"{len(candidate_failures_10)}"
    )

    for (
        query_id,
        recall,
        missing,
    ) in candidate_failures_10:
        print(
            f"  {query_id}: "
            f"Recall@10="
            f"{recall:.3f} "
            f"missing={missing}"
        )

    print()
    print(
        "=== Reranking opportunities "
        "within top 10 ==="
    )

    print(
        f"Count: "
        f"{len(reranking_opportunities_10)}"
    )

    for (
        query_id,
        actual,
        oracle,
    ) in reranking_opportunities_10:
        print(
            f"  {query_id}: "
            f"actual R@3="
            f"{actual:.3f} "
            f"oracle="
            f"{oracle:.3f}"
        )


if __name__ == "__main__":
    main()