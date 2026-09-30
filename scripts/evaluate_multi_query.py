import json
import statistics
from collections import defaultdict
from pathlib import Path

from rootlens.evaluation.benchmark import (
    validate_benchmark,
)
from rootlens.evaluation.retrieval_metrics import (
    ndcg_at_k,
    oracle_ndcg_at_k_from_candidates,
    oracle_recall_at_k_from_candidates,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from rootlens.retrieval.dense_retriever import (
    BGEEncoder,
    DenseRetriever,
)
from rootlens.retrieval.multi_query_retriever import (
    MultiQueryRetriever,
)
from rootlens.retrieval.query_rewriter import (
    StaticQueryRewriter,
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

REWRITES_FILE = (
    BENCHMARK_DIR
    / "dev_rewrites_v1.json"
)


NUM_REWRITES = 3
CANDIDATES_PER_QUERY = 10
RRF_K = 60


METRIC_NAMES = (
    "Precision@1",
    "Recall@1",
    "Recall@3",
    "Recall@5",
    "Recall@10",
    "MRR@3",
    "nDCG@3",
    "nDCG@5",
)


KNOWN_CANDIDATE_FAILURES = {
    "dev-008",
    "dev-015",
    "dev-020",
    "dev-021",
    "dev-022",
    "dev-023",
}


def mean(
    values,
) -> float:

    if not values:
        return 0.0

    return (
        sum(values)
        / len(values)
    )


def load_documents():

    documents = {}

    for path in sorted(
        KNOWLEDGE_DIR.glob(
            "*.md"
        )
    ):
        content = (
            path.read_text(
                encoding="utf-8"
            )
            .strip()
        )

        if not content:
            raise ValueError(
                f"Empty document: "
                f"{path.name}"
            )

        documents[
            path.name
        ] = content

    return documents


def load_queries():

    return json.loads(
        DEV_FILE.read_text(
            encoding="utf-8"
        )
    )


def load_rewrites():

    data = json.loads(
        REWRITES_FILE.read_text(
            encoding="utf-8"
        )
    )

    mapping = {
        item["query"]:
            item["rewrites"]
        for item in data["items"]
    }

    return (
        data,
        mapping,
    )


def relevant_documents(
    relevance,
):

    return {
        document_id
        for (
            document_id,
            grade,
        ) in relevance.items()
        if grade > 0
    }


def compute_ranking_metrics(
    retrieved,
    relevance,
):

    relevant = (
        relevant_documents(
            relevance
        )
    )

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

        "Recall@10":
            recall_at_k(
                retrieved,
                relevant,
                k=10,
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


def candidate_set_recall(
    candidates,
    relevance,
):

    relevant = (
        relevant_documents(
            relevance
        )
    )

    if not relevant:
        return 0.0

    return (
        len(
            set(candidates)
            & relevant
        )
        / len(relevant)
    )


def main():

    documents = (
        load_documents()
    )

    queries = (
        load_queries()
    )

    rewrite_data, rewrite_mapping = (
        load_rewrites()
    )

    validate_benchmark(
        documents,
        queries,
    )

    print(
        "Experiment 010 — "
        "Multi-Query Retrieval"
    )

    print(
        f"DEV only | "
        f"documents={len(documents)} "
        f"| queries={len(queries)}"
    )

    metadata = (
        rewrite_data[
            "metadata"
        ]
    )

    print(
        "Rewrite model: "
        f"{metadata.get('model')}"
    )

    print(
        "Prompt version: "
        f"{metadata.get('prompt_version')}"
    )

    print(
        f"rewrites={NUM_REWRITES} "
        f"| candidates/query="
        f"{CANDIDATES_PER_QUERY} "
        f"| RRF k={RRF_K}"
    )

    dense = DenseRetriever(
        documents,
        encoder=BGEEncoder(),
    )

    rewriter = (
        StaticQueryRewriter(
            rewrite_mapping
        )
    )

    multi = (
        MultiQueryRetriever(
            retriever=dense,
            query_rewriter=rewriter,
            num_rewrites=(
                NUM_REWRITES
            ),
            candidates_per_query=(
                CANDIDATES_PER_QUERY
            ),
            rrf_k=RRF_K,
        )
    )

    dense_metrics = defaultdict(
        list
    )

    multi_metrics = defaultdict(
        list
    )

    dense_by_category = defaultdict(
        lambda: defaultdict(
            list
        )
    )

    multi_by_category = defaultdict(
        lambda: defaultdict(
            list
        )
    )

    dense_candidate_recall = []
    union_candidate_recall = []

    dense_oracle_r3 = []
    union_oracle_r3 = []

    dense_oracle_ndcg3 = []
    union_oracle_ndcg3 = []

    union_sizes = []

    query_results = {}

    for example in queries:

        query = example[
            "query"
        ]

        relevance = example[
            "relevance"
        ]

        category = example[
            "category"
        ]

        dense_results = (
            dense.search(
                query,
                k=10,
            )
        )

        dense_ids = [
            document_id
            for (
                document_id,
                _,
            ) in dense_results
        ]

        multi_result = (
            multi.search_with_details(
                query,
                k=10,
            )
        )

        fused_ids = [
            document_id
            for (
                document_id,
                _,
            ) in (
                multi_result
                .fused_results
            )
        ]

        union_ids = (
            multi_result
            .union_document_ids
        )

        baseline_metrics = (
            compute_ranking_metrics(
                dense_ids,
                relevance,
            )
        )

        expanded_metrics = (
            compute_ranking_metrics(
                fused_ids,
                relevance,
            )
        )

        for (
            metric_name,
            value,
        ) in (
            baseline_metrics.items()
        ):

            dense_metrics[
                metric_name
            ].append(
                value
            )

            dense_by_category[
                category
            ][
                metric_name
            ].append(
                value
            )

        for (
            metric_name,
            value,
        ) in (
            expanded_metrics.items()
        ):

            multi_metrics[
                metric_name
            ].append(
                value
            )

            multi_by_category[
                category
            ][
                metric_name
            ].append(
                value
            )

        dense_candidate_recall.append(
            candidate_set_recall(
                dense_ids,
                relevance,
            )
        )

        union_candidate_recall.append(
            candidate_set_recall(
                union_ids,
                relevance,
            )
        )

        relevant = (
            relevant_documents(
                relevance
            )
        )

        dense_oracle_r3.append(
            oracle_recall_at_k_from_candidates(
                dense_ids,
                relevant,
                k=3,
            )
        )

        union_oracle_r3.append(
            oracle_recall_at_k_from_candidates(
                union_ids,
                relevant,
                k=3,
            )
        )

        dense_oracle_ndcg3.append(
            oracle_ndcg_at_k_from_candidates(
                dense_ids,
                relevance,
                k=3,
            )
        )

        union_oracle_ndcg3.append(
            oracle_ndcg_at_k_from_candidates(
                union_ids,
                relevance,
                k=3,
            )
        )

        union_sizes.append(
            len(union_ids)
        )

        query_results[
            example["query_id"]
        ] = {
            "query":
                query,

            "rewrites":
                multi_result
                .expanded_queries[1:],

            "dense_ids":
                dense_ids,

            "union_ids":
                union_ids,

            "fused_ids":
                fused_ids,

            "dense_metrics":
                baseline_metrics,

            "multi_metrics":
                expanded_metrics,

            "relevance":
                relevance,
        }

    print()
    print(
        "=== Dense BGE Baseline ==="
    )

    for name in METRIC_NAMES:

        print(
            f"{name}: "
            f"{mean(dense_metrics[name]):.4f}"
        )

    print()
    print(
        "=== Multi-Query + RRF ==="
    )

    for name in METRIC_NAMES:

        print(
            f"{name}: "
            f"{mean(multi_metrics[name]):.4f}"
        )

    print()
    print(
        "=== Aggregate Delta ==="
    )

    for name in METRIC_NAMES:

        delta = (
            mean(
                multi_metrics[
                    name
                ]
            )
            -
            mean(
                dense_metrics[
                    name
                ]
            )
        )

        print(
            f"{name}: "
            f"{delta:+.4f}"
        )

    print()
    print(
        "=== Candidate Generation ==="
    )

    print(
        "Dense candidate recall: "
        f"{mean(dense_candidate_recall):.4f}"
    )

    print(
        "Multi-query union recall: "
        f"{mean(union_candidate_recall):.4f}"
    )

    print(
        "Dense oracle Recall@3: "
        f"{mean(dense_oracle_r3):.4f}"
    )

    print(
        "Union oracle Recall@3: "
        f"{mean(union_oracle_r3):.4f}"
    )

    print(
        "Dense oracle nDCG@3: "
        f"{mean(dense_oracle_ndcg3):.4f}"
    )

    print(
        "Union oracle nDCG@3: "
        f"{mean(union_oracle_ndcg3):.4f}"
    )

    print(
        "Average union size: "
        f"{mean(union_sizes):.2f}"
    )

    print(
        "Median union size: "
        f"{statistics.median(union_sizes):.2f}"
    )

    print()
    print(
        "=== Results by Category ==="
    )

    for category in sorted(
        dense_by_category
    ):

        print()
        print(
            category
        )

        print(
            "  Dense: "
            f'R@3='
            f'{mean(dense_by_category[category]["Recall@3"]):.4f} '
            f'R@10='
            f'{mean(dense_by_category[category]["Recall@10"]):.4f} '
            f'nDCG@3='
            f'{mean(dense_by_category[category]["nDCG@3"]):.4f}'
        )

        print(
            "  Multi: "
            f'R@3='
            f'{mean(multi_by_category[category]["Recall@3"]):.4f} '
            f'R@10='
            f'{mean(multi_by_category[category]["Recall@10"]):.4f} '
            f'nDCG@3='
            f'{mean(multi_by_category[category]["nDCG@3"]):.4f}'
        )

    print()
    print(
        "=== Known Candidate Failures ==="
    )

    for query_id in sorted(
        KNOWN_CANDIDATE_FAILURES
    ):

        result = (
            query_results[
                query_id
            ]
        )

        relevance = (
            result[
                "relevance"
            ]
        )

        relevant = (
            relevant_documents(
                relevance
            )
        )

        dense_set = set(
            result[
                "dense_ids"
            ]
        )

        union_set = set(
            result[
                "union_ids"
            ]
        )

        fused_set = set(
            result[
                "fused_ids"
            ]
        )

        baseline_missing = (
            relevant
            - dense_set
        )

        recovered_by_union = (
            baseline_missing
            & union_set
        )

        recovered_in_rrf_top10 = (
            baseline_missing
            & fused_set
        )

        print()
        print(
            f"{query_id}: "
            f"{result['query']}"
        )

        print(
            "  Rewrites:"
        )

        for rewrite in (
            result[
                "rewrites"
            ]
        ):
            print(
                f"    - {rewrite}"
            )

        print(
            "  Missing from dense top10: "
            f"{sorted(baseline_missing)}"
        )

        print(
            "  Recovered by union: "
            f"{sorted(recovered_by_union)}"
        )

        print(
            "  Survives RRF top10: "
            f"{sorted(recovered_in_rrf_top10)}"
        )

        print(
            "  Recall@3: "
            f'{result["dense_metrics"]["Recall@3"]:.3f}'
            " -> "
            f'{result["multi_metrics"]["Recall@3"]:.3f}'
        )

        print(
            "  nDCG@3: "
            f'{result["dense_metrics"]["nDCG@3"]:.3f}'
            " -> "
            f'{result["multi_metrics"]["nDCG@3"]:.3f}'
        )

    generation_latencies = [
        item.get(
            "latency_ms",
            0.0,
        )
        for item in (
            rewrite_data[
                "items"
            ]
        )
    ]

    if generation_latencies:

        print()
        print(
            "=== Offline Rewrite Generation Latency ==="
        )

        print(
            "Mean: "
            f"{statistics.mean(generation_latencies):.2f} ms"
        )

        print(
            "Median: "
            f"{statistics.median(generation_latencies):.2f} ms"
        )

        print(
            "Note: rewrites are frozen for this "
            "benchmark, so these API latencies are "
            "not included in retrieval timing."
        )


if __name__ == "__main__":
    main()