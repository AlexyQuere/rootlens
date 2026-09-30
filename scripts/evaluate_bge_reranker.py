import gc
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path

import torch

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
    BGEReranker,
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


METRIC_NAMES = (
    "Precision@1",
    "Recall@1",
    "Recall@3",
    "Recall@5",
    "MRR@3",
    "nDCG@3",
    "nDCG@5",
)


def choose_device() -> str:
    if (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    ):
        return "mps"

    if torch.cuda.is_available():
        return "cuda"

    return "cpu"


def synchronize_device(
    device: str,
) -> None:
    """Synchronize asynchronous accelerators before timing."""

    if device == "mps":
        torch.mps.synchronize()

    elif device.startswith(
        "cuda"
    ):
        torch.cuda.synchronize()


def clear_device_cache(
    device: str,
) -> None:
    gc.collect()

    if device == "mps":
        torch.mps.empty_cache()

    elif device.startswith(
        "cuda"
    ):
        torch.cuda.empty_cache()


def load_documents() -> dict[str, str]:
    documents = {}

    for path in sorted(
        KNOWLEDGE_DIR.glob(
            "*.md"
        )
    ):
        content = path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            raise ValueError(
                f"Empty document: "
                f"{path.name}"
            )

        documents[
            path.name
        ] = content

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

    return (
        sum(values)
        / len(values)
    )


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
        "Precision@1":
            precision_at_k(
                retrieved,
                relevant,
                k=1,
            ),

        "Recall@1":
            recall_at_k(
                retrieved,
                relevant,
                k=1,
            ),

        "Recall@3":
            recall_at_k(
                retrieved,
                relevant,
                k=3,
            ),

        "Recall@5":
            recall_at_k(
                retrieved,
                relevant,
                k=5,
            ),

        "MRR@3":
            reciprocal_rank(
                retrieved[:3],
                relevant,
            ),

        "nDCG@3":
            ndcg_at_k(
                retrieved,
                relevance,
                k=3,
            ),

        "nDCG@5":
            ndcg_at_k(
                retrieved,
                relevance,
                k=5,
            ),
    }

def evaluate(
    name: str,
    retriever,
    queries: list[dict],
    timing_device: str | None = None,
):
    aggregate = defaultdict(
        list
    )

    by_category = defaultdict(
        lambda: defaultdict(
            list
        )
    )

    rankings = {}

    latencies_ms = []

    for example in queries:

        if timing_device:
            synchronize_device(
                timing_device
            )

        start = (
            time.perf_counter()
        )

        results = retriever.search(
            example["query"],
            k=5,
        )

        if timing_device:
            synchronize_device(
                timing_device
            )

        elapsed_ms = (
            time.perf_counter()
            - start
        ) * 1000.0

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

        metrics = (
            compute_metrics(
                retrieved,
                example["relevance"],
            )
        )

        for (
            metric_name,
            value,
        ) in metrics.items():

            aggregate[
                metric_name
            ].append(
                value
            )

            by_category[
                example["category"]
            ][
                metric_name
            ].append(
                value
            )

    summary = {
        metric_name:
            mean(
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
            f"{summary[metric_name]:.4f}"
        )

    print()
    print(
        "By category:"
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
            f"  {category}"
        )

        print(
            "    "
            f'P@1='
            f'{mean(values["Precision@1"]):.4f} '
            f'R@3='
            f'{mean(values["Recall@3"]):.4f} '
            f'R@5='
            f'{mean(values["Recall@5"]):.4f} '
            f'nDCG@3='
            f'{mean(values["nDCG@3"]):.4f}'
        )

    print()
    print(
        "Latency:"
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
        latencies_ms,
    )

def print_delta(
    baseline: dict[str, float],
    experiment: dict[str, float],
    label: str,
) -> None:

    print()
    print(
        f"=== Delta: {label} ==="
    )

    for metric_name in METRIC_NAMES:

        delta = (
            experiment[
                metric_name
            ]
            - baseline[
                metric_name
            ]
        )

        print(
            f"{metric_name}: "
            f"{delta:+.4f}"
        )


def print_query_changes(
    queries: list[dict],
    dense_rankings,
    bge_rankings,
) -> None:

    print()
    print(
        "=== BGE Reranker "
        "Query-Level Changes ==="
    )

    for example in queries:

        query_id = (
            example[
                "query_id"
            ]
        )

        dense = (
            dense_rankings[
                query_id
            ]
        )

        reranked = (
            bge_rankings[
                query_id
            ]
        )

        if (
            dense[:3]
            == reranked[:3]
        ):
            continue

        dense_metrics = (
            compute_metrics(
                dense,
                example["relevance"],
            )
        )

        reranked_metrics = (
            compute_metrics(
                reranked,
                example["relevance"],
            )
        )

        print()
        print(
            f"{query_id}: "
            f"{example['query']}"
        )

        print(
            "  Dense top 3:"
        )

        for document_id in dense[:3]:
            print(
                f"    {document_id}"
            )

        print(
            "  BGE reranked top 3:"
        )

        for document_id in reranked[:3]:
            print(
                f"    {document_id}"
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


def main() -> None:

    documents = (
        load_documents()
    )

    queries = (
        load_queries()
    )

    validate_benchmark(
        documents,
        queries,
    )

    device = (
        choose_device()
    )

    print(
        "Experiment 009 — "
        "BGE Reranker"
    )

    print(
        f"DEV only | "
        f"documents={len(documents)} "
        f"| queries={len(queries)} "
        f"| candidate_k={CANDIDATE_K}"
    )

    print(
        f"Reranker device: "
        f"{device}"
    )

    dense_retriever = (
        DenseRetriever(
            documents,
            encoder=BGEEncoder(),
        )
    )

    (
        dense_summary,
        dense_rankings,
        dense_latencies,
    ) = evaluate(
        "Dense BGE baseline",
        dense_retriever,
        queries,
    )

    print()
    print(
        "Loading MiniLM reranker..."
    )

    minilm_reranker = (
        CrossEncoderReranker(
            device=device
        )
    )

    minilm_retriever = (
        RerankedRetriever(
            candidate_retriever=(
                dense_retriever
            ),
            documents=documents,
            reranker=(
                minilm_reranker
            ),
            candidate_k=(
                CANDIDATE_K
            ),
        )
    )

    (
        minilm_summary,
        _,
        minilm_latencies,
    ) = evaluate(
        "Dense + MiniLM reranker",
        minilm_retriever,
        queries,
        timing_device=device,
    )

    del minilm_retriever
    del minilm_reranker

    clear_device_cache(
        device
    )

    print()
    print(
        "Loading BGE reranker..."
    )

    bge_reranker = (
        BGEReranker(
            device=device,
            batch_size=4,
        )
    )

    bge_retriever = (
        RerankedRetriever(
            candidate_retriever=(
                dense_retriever
            ),
            documents=documents,
            reranker=(
                bge_reranker
            ),
            candidate_k=(
                CANDIDATE_K
            ),
        )
    )

    (
        bge_summary,
        bge_rankings,
        bge_latencies,
    ) = evaluate(
        "Dense + BGE reranker",
        bge_retriever,
        queries,
        timing_device=device,
    )

    print_delta(
        dense_summary,
        minilm_summary,
        "MiniLM vs Dense",
    )

    print_delta(
        dense_summary,
        bge_summary,
        "BGE reranker vs Dense",
    )

    print_query_changes(
        queries,
        dense_rankings,
        bge_rankings,
    )


if __name__ == "__main__":
    main()