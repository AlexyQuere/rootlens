import json
from collections import defaultdict
from pathlib import Path

from rootlens.evaluation.benchmark import (
    validate_benchmark,
)
from rootlens.evaluation.retrieval_metrics import (
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from rootlens.retrieval.chunked_dense_retriever import (
    ChunkedDenseRetriever,
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


METRIC_NAMES = (
    "Precision@1",
    "Recall@1",
    "Recall@3",
    "Recall@5",
    "MRR@3",
    "nDCG@3",
    "nDCG@5",
)


def load_documents() -> dict[str, str]:
    documents: dict[str, str] = {}

    for path in sorted(
        KNOWLEDGE_DIR.glob("*.md")
    ):
        content = path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            raise ValueError(
                "Knowledge document is empty: "
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


def compute_metrics(
    retrieved: list[str],
    relevance: dict[str, int],
) -> dict[str, float]:
    binary_relevant = {
        document_id
        for document_id, grade
        in relevance.items()
        if grade > 0
    }

    return {
        "Precision@1": precision_at_k(
            retrieved,
            binary_relevant,
            k=1,
        ),
        "Recall@1": recall_at_k(
            retrieved,
            binary_relevant,
            k=1,
        ),
        "Recall@3": recall_at_k(
            retrieved,
            binary_relevant,
            k=3,
        ),
        "Recall@5": recall_at_k(
            retrieved,
            binary_relevant,
            k=5,
        ),
        "MRR@3": reciprocal_rank(
            retrieved[:3],
            binary_relevant,
        ),
        "nDCG@3": ndcg_at_k(
            retrieved,
            relevance,
            k=3,
        ),
        "nDCG@5": ndcg_at_k(
            retrieved,
            relevance,
            k=5,
        ),
    }


def maximum_recall_at_k(
    relevance: dict[str, int],
    k: int,
) -> float:
    """Maximum Recall@k achievable for a query.

    Example:

    4 relevant documents
    k = 3

    Maximum possible Recall@3 = 3 / 4 = 0.75
    """

    relevant_count = sum(
        grade > 0
        for grade in relevance.values()
    )

    if relevant_count == 0:
        return 0.0

    return (
        min(
            k,
            relevant_count,
        )
        / relevant_count
    )


def evaluate_retriever(
    name: str,
    retriever,
    queries: list[dict],
) -> dict[str, float]:
    aggregate: dict[
        str,
        list[float],
    ] = defaultdict(list)

    by_category: dict[
        str,
        dict[str, list[float]],
    ] = defaultdict(
        lambda: defaultdict(list)
    )

    direct_relevance_failures = []

    suboptimal_recall_queries = []

    for example in queries:
        results = retriever.search(
            example["query"],
            k=5,
        )

        retrieved = [
            document_id
            for document_id, _
            in results
        ]

        metrics = compute_metrics(
            retrieved,
            example["relevance"],
        )

        for (
            metric_name,
            value,
        ) in metrics.items():
            aggregate[
                metric_name
            ].append(value)

            by_category[
                example["category"]
            ][
                metric_name
            ].append(value)

        directly_relevant = {
            document_id
            for document_id, grade
            in example[
                "relevance"
            ].items()
            if grade == 2
        }

        top_document = (
            retrieved[0]
            if retrieved
            else None
        )

        if (
            top_document
            not in directly_relevant
        ):
            direct_relevance_failures.append(
                (
                    example["query_id"],
                    example["query"],
                    top_document,
                )
            )

        max_recall = (
            maximum_recall_at_k(
                example["relevance"],
                k=3,
            )
        )

        actual_recall = (
            metrics["Recall@3"]
        )

        if (
            actual_recall
            < max_recall - 1e-12
        ):
            relevant_documents = {
                document_id
                for document_id, grade
                in example[
                    "relevance"
                ].items()
                if grade > 0
            }

            missing = sorted(
                relevant_documents
                - set(
                    retrieved[:3]
                )
            )

            suboptimal_recall_queries.append(
                (
                    example[
                        "query_id"
                    ],
                    actual_recall,
                    max_recall,
                    missing,
                )
            )

    aggregated_results = {
        metric_name: mean(
            aggregate[
                metric_name
            ]
        )
        for metric_name
        in METRIC_NAMES
    }

    print()
    print(
        f"=== {name} ==="
    )

    for metric_name in METRIC_NAMES:
        print(
            f"{metric_name}: "
            f"{aggregated_results[metric_name]:.4f}"
        )

    print()
    print("By category:")

    for category in sorted(
        by_category
    ):
        values = (
            by_category[
                category
            ]
        )

        print(
            f"  {category}"
        )

        print(
            "    "
            "Precision@1="
            f'{mean(values["Precision@1"]):.4f} '
            "Recall@3="
            f'{mean(values["Recall@3"]):.4f} '
            "Recall@5="
            f'{mean(values["Recall@5"]):.4f} '
            "nDCG@3="
            f'{mean(values["nDCG@3"]):.4f}'
        )

    print()
    print(
        "Top-1 direct-relevance "
        "failures: "
        f"{len(direct_relevance_failures)}"
    )

    for (
        query_id,
        query,
        top_document,
    ) in direct_relevance_failures:
        print(
            f"  {query_id}: "
            f"top={top_document!r} "
            f"| {query}"
        )

    print()
    print(
        "Suboptimal Recall@3 "
        "queries: "
        f"{len(suboptimal_recall_queries)}"
    )

    for (
        query_id,
        recall,
        max_recall,
        missing,
    ) in suboptimal_recall_queries:
        print(
            f"  {query_id}: "
            f"Recall@3={recall:.3f} "
            f"max={max_recall:.3f} "
            f"missing={missing}"
        )

    return aggregated_results


def print_comparison(
    results: dict[
        str,
        dict[str, float],
    ],
) -> None:
    print()
    print(
        "=== Chunking comparison ==="
    )

    header = (
        f'{"Configuration":<24}'
        f'{"P@1":>9}'
        f'{"R@3":>9}'
        f'{"R@5":>9}'
        f'{"nDCG@3":>11}'
        f'{"nDCG@5":>11}'
    )

    print(header)

    print(
        "-" * len(header)
    )

    for (
        configuration,
        metrics,
    ) in results.items():
        print(
            f"{configuration:<24}"
            f'{metrics["Precision@1"]:>9.4f}'
            f'{metrics["Recall@3"]:>9.4f}'
            f'{metrics["Recall@5"]:>9.4f}'
            f'{metrics["nDCG@3"]:>11.4f}'
            f'{metrics["nDCG@5"]:>11.4f}'
        )


def main() -> None:
    documents = load_documents()
    queries = load_queries()

    validate_benchmark(
        documents,
        queries,
    )

    print(
        "Experiment 006 — "
        "Chunking and Retrieval Granularity"
    )

    print(
        f"DEV only | "
        f"documents={len(documents)} "
        f"| queries={len(queries)}"
    )

    # One encoder instance is deliberately
    # shared across all three configurations.
    #
    # This avoids loading the same BGE model
    # three times.
    encoder = BGEEncoder()

    whole_document_retriever = (
        DenseRetriever(
            documents,
            encoder=encoder,
        )
    )

    chunk_64_retriever = (
        ChunkedDenseRetriever(
            documents,
            encoder=encoder,
            chunk_size_words=64,
            overlap_words=16,
        )
    )

    chunk_128_retriever = (
        ChunkedDenseRetriever(
            documents,
            encoder=encoder,
            chunk_size_words=128,
            overlap_words=32,
        )
    )

    print()
    print(
        "Chunk statistics:"
    )

    print(
        "  Whole document units: "
        f"{len(documents)}"
    )

    print(
        "  64/16 chunks: "
        f"{len(chunk_64_retriever.chunks)}"
    )

    print(
        "  128/32 chunks: "
        f"{len(chunk_128_retriever.chunks)}"
    )

    results = {}

    results[
        "Whole document"
    ] = evaluate_retriever(
        "Dense — Whole document",
        whole_document_retriever,
        queries,
    )

    results[
        "Chunk 64 / 16"
    ] = evaluate_retriever(
        "Dense — 64 words / 16 overlap",
        chunk_64_retriever,
        queries,
    )

    results[
        "Chunk 128 / 32"
    ] = evaluate_retriever(
        "Dense — 128 words / 32 overlap",
        chunk_128_retriever,
        queries,
    )

    print_comparison(
        results
    )


if __name__ == "__main__":
    main()