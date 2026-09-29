import argparse
import json
from collections import defaultdict
from pathlib import Path

from rootlens.evaluation.benchmark import (
    validate_benchmark,
    validate_query_split,
)
from rootlens.evaluation.retrieval_metrics import (
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from rootlens.retrieval.bm25_retriever import BM25Retriever
from rootlens.retrieval.dense_retriever import BGEEncoder, DenseRetriever
from rootlens.retrieval.hybrid_retriever import HybridRetriever
from rootlens.retrieval.tfidf_retriever import TfidfRetriever


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = ROOT / "data" / "benchmark_v2"
KNOWLEDGE_DIR = BENCHMARK_DIR / "knowledge"
DEV_FILE = BENCHMARK_DIR / "dev_queries.json"
TEST_FILE = BENCHMARK_DIR / "test_queries.json"

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

    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8").strip()

        if not content:
            raise ValueError(
                f"Knowledge document is empty: {path.name}"
            )

        documents[path.name] = content

    return documents


def load_queries(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def compute_metrics(
    retrieved: list[str],
    relevance: dict[str, int],
) -> dict[str, float]:
    binary_relevant = {
        document_id
        for document_id, grade in relevance.items()
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


def evaluate_retriever(
    name: str,
    retriever,
    queries: list[dict],
    corpus_size: int,
) -> None:
    aggregate: dict[str, list[float]] = defaultdict(list)
    by_category: dict[
        str,
        dict[str, list[float]],
    ] = defaultdict(lambda: defaultdict(list))

    top1_failures: list[tuple[str, str, str | None]] = []
    recall_failures: list[tuple[str, float, list[str]]] = []

    for example in queries:
        if isinstance(retriever, HybridRetriever):
            results = retriever.search(
                example["query"],
                k=min(5, corpus_size),
                candidate_k=corpus_size,
            )
        else:
            results = retriever.search(
                example["query"],
                k=min(5, corpus_size),
            )

        retrieved = [
            document_id
            for document_id, _ in results
        ]

        metrics = compute_metrics(
            retrieved,
            example["relevance"],
        )

        for metric_name, value in metrics.items():
            aggregate[metric_name].append(value)
            by_category[
                example["category"]
            ][metric_name].append(value)

        directly_relevant = {
            document_id
            for document_id, grade
            in example["relevance"].items()
            if grade == 2
        }

        top_document = (
            retrieved[0]
            if retrieved
            else None
        )

        if top_document not in directly_relevant:
            top1_failures.append(
                (
                    example["query_id"],
                    example["query"],
                    top_document,
                )
            )

        if metrics["Recall@3"] < 1.0:
            missing = sorted(
                {
                    document_id
                    for document_id, grade
                    in example["relevance"].items()
                    if grade > 0
                }
                - set(retrieved[:3])
            )

            recall_failures.append(
                (
                    example["query_id"],
                    metrics["Recall@3"],
                    missing,
                )
            )

    print()
    print(f"=== {name} ===")

    for metric_name in METRIC_NAMES:
        print(
            f"{metric_name}: "
            f"{mean(aggregate[metric_name]):.4f}"
        )

    print()
    print("By category:")

    for category in sorted(by_category):
        values = by_category[category]

        print(f"  {category}")

        print(
            "    Precision@1="
            f'{mean(values["Precision@1"]):.4f} '
            "Recall@3="
            f'{mean(values["Recall@3"]):.4f} '
            "nDCG@3="
            f'{mean(values["nDCG@3"]):.4f}'
        )

    print()
    print(
        f"Top-1 direct-relevance failures: "
        f"{len(top1_failures)}"
    )

    for query_id, query, top_document in top1_failures:
        print(
            f"  {query_id}: "
            f"top={top_document!r} | {query}"
        )

    print()
    print(
        f"Incomplete Recall@3 queries: "
        f"{len(recall_failures)}"
    )

    for query_id, recall, missing in recall_failures:
        print(
            f"  {query_id}: "
            f"Recall@3={recall:.3f} "
            f"missing={missing}"
        )


def build_retrievers(
    choice: str,
    documents: dict[str, str],
) -> list[tuple[str, object]]:
    retrievers: list[tuple[str, object]] = []

    bm25 = None
    dense = None

    if choice in {"tfidf", "all"}:
        retrievers.append(
            (
                "TF-IDF",
                TfidfRetriever(documents),
            )
        )

    if choice in {"bm25", "hybrid", "all"}:
        bm25 = BM25Retriever(documents)

        if choice in {"bm25", "all"}:
            retrievers.append(
                (
                    "BM25",
                    bm25,
                )
            )

    if choice in {"dense", "hybrid", "all"}:
        encoder = BGEEncoder()
        dense = DenseRetriever(
            documents,
            encoder=encoder,
        )

        if choice in {"dense", "all"}:
            retrievers.append(
                (
                    "Dense BGE",
                    dense,
                )
            )

    if choice in {"hybrid", "all"}:
        assert bm25 is not None
        assert dense is not None

        retrievers.append(
            (
                "Hybrid RRF",
                HybridRetriever(
                    lexical_retriever=bm25,
                    dense_retriever=dense,
                    rrf_k=60,
                ),
            )
        )

    return retrievers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate RootLens retrieval systems "
            "on Benchmark v2."
        )
    )

    parser.add_argument(
        "--split",
        choices=("dev", "test"),
        default="dev",
    )

    parser.add_argument(
        "--retriever",
        choices=(
            "tfidf",
            "bm25",
            "dense",
            "hybrid",
            "all",
        ),
        default="all",
    )

    parser.add_argument(
        "--confirm-test",
        action="store_true",
        help=(
            "Required to evaluate the frozen TEST set."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if (
        args.split == "test"
        and not args.confirm_test
    ):
        raise SystemExit(
            "TEST is frozen. "
            "Re-run with --confirm-test only at "
            "an explicit milestone checkpoint."
        )

    documents = load_documents()
    dev_queries = load_queries(DEV_FILE)
    test_queries = load_queries(TEST_FILE)

    validate_benchmark(
        documents,
        dev_queries,
    )

    validate_benchmark(
        documents,
        test_queries,
    )

    validate_query_split(
        dev_queries,
        test_queries,
    )

    queries = (
        dev_queries
        if args.split == "dev"
        else test_queries
    )

    print(
        f"Benchmark v2 | split={args.split.upper()} "
        f"| documents={len(documents)} "
        f"| queries={len(queries)}"
    )

    retrievers = build_retrievers(
        args.retriever,
        documents,
    )

    for name, retriever in retrievers:
        evaluate_retriever(
            name,
            retriever,
            queries,
            corpus_size=len(documents),
        )


if __name__ == "__main__":
    main()
