import json
import statistics
import time
import torch
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
from rootlens.retrieval.dense_retriever import (
    BGEEncoder,
    DenseRetriever,
)
from rootlens.retrieval.reranker import (
    CrossEncoderReranker,
    RerankedRetriever,
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

CANDIDATE_K = 10

RERANKING_OPPORTUNITY_IDS = {
    "dev-002",
    "dev-005",
    "dev-006",
    "dev-007",
    "dev-010",
    "dev-011",
    "dev-012",
    "dev-013",
    "dev-015",
    "dev-017",
    "dev-021",
    "dev-022",
}

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
    documents = {}

    for path in sorted(
        KNOWLEDGE_DIR.glob("*.md")
    ):
        content = path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            raise ValueError(
                f"Empty document: {path.name}"
            )

        documents[path.name] = content

    return documents


def load_queries() -> list[dict]:
    return json.loads(
        DEV_FILE.read_text(
            encoding="utf-8"
        )
    )


def mean(values: list[float]) -> float:
    if not values:
        return 0.0

    return sum(values) / len(values)

def choose_reranker_device() -> str:
    if (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    ):
        return "mps"

    if torch.cuda.is_available():
        return "cuda"

    return "cpu"

def compute_metrics(
    retrieved: list[str],
    relevance: dict[str, int],
) -> dict[str, float]:
    relevant = {
        document_id
        for document_id, grade
        in relevance.items()
        if grade > 0
    }

    return {
        "Precision@1": precision_at_k(
            retrieved,
            relevant,
            k=1,
        ),
        "Recall@1": recall_at_k(
            retrieved,
            relevant,
            k=1,
        ),
        "Recall@3": recall_at_k(
            retrieved,
            relevant,
            k=3,
        ),
        "Recall@5": recall_at_k(
            retrieved,
            relevant,
            k=5,
        ),
        "MRR@3": reciprocal_rank(
            retrieved[:3],
            relevant,
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


def evaluate(
    name: str,
    retriever,
    queries: list[dict],
    measure_latency: bool = False,
):
    aggregate = defaultdict(list)
    by_category = defaultdict(
        lambda: defaultdict(list)
    )
    rankings = {}
    latencies_ms = []

    for example in queries:
        start = time.perf_counter()

        results = retriever.search(
            example["query"],
            k=5,
        )

        elapsed_ms = (
            time.perf_counter()
            - start
        ) * 1000.0

        if measure_latency:
            latencies_ms.append(
                elapsed_ms
            )

        retrieved = [
            document_id
            for document_id, _
            in results
        ]

        rankings[
            example["query_id"]
        ] = retrieved

        metrics = compute_metrics(
            retrieved,
            example["relevance"],
        )

        for metric_name, value in metrics.items():
            aggregate[
                metric_name
            ].append(value)

            by_category[
                example["category"]
            ][metric_name].append(
                value
            )

    summary = {
        metric_name: mean(
            aggregate[metric_name]
        )
        for metric_name in METRIC_NAMES
    }

    print()
    print(
        f"=== {name} ==="
    )

    for metric_name in METRIC_NAMES:
        print(
            f"{metric_name}: "
            f"{summary[metric_name]:.4f}"
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
            f'P@1={mean(values["Precision@1"]):.4f} '
            f'R@3={mean(values["Recall@3"]):.4f} '
            f'R@5={mean(values["Recall@5"]):.4f} '
            f'nDCG@3={mean(values["nDCG@3"]):.4f}'
        )

    if latencies_ms:
        print()
        print(
            "Reranked search latency "
            "(includes candidate retrieval):"
        )

        print(
            "  mean: "
            f"{statistics.mean(latencies_ms):.2f} ms"
        )

        print(
            "  median: "
            f"{statistics.median(latencies_ms):.2f} ms"
        )

        sorted_latencies = sorted(
            latencies_ms
        )

        p95_index = min(
            len(sorted_latencies) - 1,
            int(
                0.95
                * len(sorted_latencies)
            ),
        )

        print(
            "  p95: "
            f"{sorted_latencies[p95_index]:.2f} ms"
        )

    return (
        summary,
        rankings,
    )


def main() -> None:
    documents = load_documents()
    queries = load_queries()

    validate_benchmark(
        documents,
        queries,
    )

    print(
        "Experiment 008 — "
        "Cross-Encoder Reranking"
    )

    print(
        f"DEV only | "
        f"documents={len(documents)} "
        f"| queries={len(queries)} "
        f"| candidate_k={CANDIDATE_K}"
    )

    encoder = BGEEncoder()

    dense_retriever = (
        DenseRetriever(
            documents,
            encoder=encoder,
        )
    )

    reranker_device = (
        choose_reranker_device()
    )

    print(
        f"Cross-encoder device: "
        f"{reranker_device}"
    )

    cross_encoder = (
        CrossEncoderReranker(
            device=reranker_device,
        )
    )

    reranked_retriever = (
        RerankedRetriever(
            candidate_retriever=(
                dense_retriever
            ),
            documents=documents,
            reranker=cross_encoder,
            candidate_k=CANDIDATE_K,
        )
    )

    (
        dense_summary,
        dense_rankings,
    ) = evaluate(
        "Dense BGE baseline",
        dense_retriever,
        queries,
    )

    (
        reranked_summary,
        reranked_rankings,
    ) = evaluate(
        "Dense BGE + Cross-Encoder",
        reranked_retriever,
        queries,
        measure_latency=True,
    )

    print()
    print(
        "=== Aggregate Delta ==="
    )

    for metric_name in METRIC_NAMES:
        delta = (
            reranked_summary[
                metric_name
            ]
            - dense_summary[
                metric_name
            ]
        )

        print(
            f"{metric_name}: "
            f"{delta:+.4f}"
        )

    print()
    print(
        "=== Known Reranking "
        "Opportunity Queries ==="
    )

    for example in queries:
        query_id = (
            example["query_id"]
        )

        if (
            query_id
            not in RERANKING_OPPORTUNITY_IDS
        ):
            continue

        dense_metrics = compute_metrics(
            dense_rankings[
                query_id
            ],
            example["relevance"],
        )

        reranked_metrics = compute_metrics(
            reranked_rankings[
                query_id
            ],
            example["relevance"],
        )

        print()
        print(
            f"{query_id}: "
            f"{example['query']}"
        )

        print(
            "  Dense top 3: "
            f"{dense_rankings[query_id][:3]}"
        )

        print(
            "  Reranked top 3: "
            f"{reranked_rankings[query_id][:3]}"
        )

        print(
            "  Recall@3: "
            f'{dense_metrics["Recall@3"]:.3f}'
            " -> "
            f'{reranked_metrics["Recall@3"]:.3f}'
        )

        print(
            "  nDCG@3: "
            f'{dense_metrics["nDCG@3"]:.3f}'
            " -> "
            f'{reranked_metrics["nDCG@3"]:.3f}'
        )


if __name__ == "__main__":
    main()
