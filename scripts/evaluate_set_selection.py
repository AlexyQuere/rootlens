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
from rootlens.retrieval.dense_retriever import (
    BGEEncoder,
    DenseRetriever,
)
from rootlens.retrieval.multi_query_retriever import (
    reciprocal_rank_fusion,
)
from rootlens.retrieval.query_rewriter import (
    StaticQueryRewriter,
)
from rootlens.retrieval.set_selection import (
    greedy_query_coverage,
    maximal_marginal_relevance,
    normalize_score_maps,
    query_coverage_value,
)
from sentence_transformers import SentenceTransformer

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


KNOWN_CANDIDATE_FAILURES = {
    "dev-008",
    "dev-015",
    "dev-020",
    "dev-021",
    "dev-022",
    "dev-023",
}


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

def mean_pairwise_similarity(
    document_ids,
    document_similarities,
):

    if len(document_ids) < 2:
        return 0.0

    values = []

    for i in range(
        len(document_ids)
    ):
        for j in range(
            i + 1,
            len(document_ids),
        ):
            values.append(
                document_similarities[
                    document_ids[i]
                ][
                    document_ids[j]
                ]
            )

    return (
        sum(values)
        / len(values)
    )

def compute_metrics(
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


def rank_of(
    document_id,
    ranking,
):

    try:
        return (
            ranking.index(
                document_id
            )
            + 1
        )

    except ValueError:
        return None

def add_metrics(
    store,
    metrics,
):

    for (
        metric_name,
        value,
    ) in metrics.items():

        store[
            metric_name
        ].append(
            value
        )


def print_summary(
    name,
    store,
):

    print()
    print(
        f"=== {name} ==="
    )

    for metric_name in (
        METRIC_NAMES
    ):

        print(
            f"{metric_name}: "
            f"{mean(store[metric_name]):.4f}"
        )

def build_document_similarities(
    documents,
):

    document_ids = sorted(
        documents
    )

    texts = [
        documents[
            document_id
        ]
        for document_id
        in document_ids
    ]

    model = SentenceTransformer(
        "BAAI/bge-small-en-v1.5"
    )

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    similarity_matrix = (
        embeddings
        @ embeddings.T
    )

    return {
        document_id: {
            other_id:
                float(
                    similarity_matrix[
                        i,
                        j,
                    ]
                )
            for j, other_id
            in enumerate(
                document_ids
            )
        }
        for i, document_id
        in enumerate(
            document_ids
        )
    }


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

    document_similarities = (
        build_document_similarities(
            documents
        )
    )

    validate_benchmark(
        documents,
        queries,
    )

    rewriter = (
        StaticQueryRewriter(
            rewrite_mapping
        )
    )

    dense = DenseRetriever(
        documents,
        encoder=BGEEncoder(),
    )

    print(
        "Experiment 012 — "
        "Set-Aware Evidence Selection"
    )

    print(
        f"DEV only | "
        f"documents={len(documents)} "
        f"| queries={len(queries)}"
    )

    print(
        "Rewrite model: "
        f"{rewrite_data['metadata'].get('model')}"
    )

    print(
        f"rewrites={NUM_REWRITES} "
        f"| candidates/query="
        f"{CANDIDATES_PER_QUERY}"
    )

    stores = {
        "Dense":
            defaultdict(list),

        "RRF":
            defaultdict(list),

        "MMR":
            defaultdict(list),

        "Coverage":
            defaultdict(list),
    }

    category_stores = {
        method:
            defaultdict(
                lambda:
                    defaultdict(
                        list
                    )
            )
        for method in stores
    }

    diagnostics = {}
    mechanism_diagnostics = {
        method: {
            "coverage_at_5": [],
            "pairwise_similarity_at_5": [],
        }
        for method in (
            "Dense",
            "RRF",
            "MMR",
            "Coverage",
        )
    }

    for example in queries:

        query = (
            example[
                "query"
            ]
        )

        relevance = (
            example[
                "relevance"
            ]
        )

        category = (
            example[
                "category"
            ]
        )

        rewrites = (
            rewriter.rewrite(
                query,
                n=NUM_REWRITES,
            )
        )

        expanded_queries = [
            query,
            *rewrites,
        ]

        top_rankings = []

        union_ids = []
        seen = set()

        for expanded_query in (
            expanded_queries
        ):

            ranking = (
                dense.search(
                    expanded_query,
                    k=(
                        CANDIDATES_PER_QUERY
                    ),
                )
            )

            top_rankings.append(
                ranking
            )

            for (
                document_id,
                _,
            ) in ranking:

                if document_id in seen:
                    continue

                seen.add(
                    document_id
                )

                union_ids.append(
                    document_id
                )

        #
        # Compute the real Dense score for every
        # union candidate against every query.
        #
        score_maps = []

        for expanded_query in (
            expanded_queries
        ):

            full_ranking = (
                dense.search(
                    expanded_query,
                    k=len(documents),
                )
            )

            full_score_map = {
                document_id:
                    score
                for (
                    document_id,
                    score,
                ) in full_ranking
            }

            missing = [
                document_id
                for document_id
                in union_ids
                if document_id
                not in full_score_map
            ]

            if missing:
                raise RuntimeError(
                    "Dense retriever did not "
                    "return scores for all "
                    "union candidates: "
                    f"{missing}"
                )

            score_maps.append(
                full_score_map
            )

        dense_ids = [
            document_id
            for (
                document_id,
                _,
            ) in top_rankings[0]
        ]

        rrf_ids = [
            document_id
            for (
                document_id,
                _,
            ) in (
                reciprocal_rank_fusion(
                    top_rankings,
                    rrf_k=RRF_K,
                )[:10]
            )
        ]   

        coverage_ranking = (
            greedy_query_coverage(
                union_ids,
                score_maps,
                k=10,
            )
        )

        coverage_ids = [
            document_id
            for document_id, _
            in coverage_ranking
        ]

        mmr_ranking = (
            maximal_marginal_relevance(
                union_ids,
                score_maps,
                document_similarities,
                k=10,
                lambda_relevance=0.5,
            )
        )

        mmr_ids = [
            document_id
            for document_id, _
            in mmr_ranking
        ]

        rankings = {
            "Dense":
                dense_ids,

            "RRF":
                rrf_ids,

            "MMR":
                mmr_ids,

            "Coverage":
                coverage_ids,
        }

        normalized_score_maps = (
            normalize_score_maps(
                union_ids,
                score_maps,
            )
        )

        for method, ranking in (
            rankings.items()
        ):

            top5 = ranking[:5]

            coverage_at_5 = (
                query_coverage_value(
                    top5,
                    normalized_score_maps,
                )
            )

            pairwise_similarity_at_5 = (
                mean_pairwise_similarity(
                    top5,
                    document_similarities,
                )
            )

            mechanism_diagnostics[
                method
            ][
                "coverage_at_5"
            ].append(
                coverage_at_5
            )

            mechanism_diagnostics[
                method
            ][
                "pairwise_similarity_at_5"
            ].append(
                pairwise_similarity_at_5
            )

        metrics_by_method = {}

        for (
            method,
            ranking,
        ) in rankings.items():

            metrics = (
                compute_metrics(
                    ranking,
                    relevance,
                )
            )

            metrics_by_method[
                method
            ] = metrics

            add_metrics(
                stores[
                    method
                ],
                metrics,
            )

            add_metrics(
                category_stores[
                    method
                ][
                    category
                ],
                metrics,
            )

        diagnostics[
            example["query_id"]
        ] = {
            "query":
                query,

            "rewrites":
                rewrites,

            "union_ids":
                union_ids,

            "rankings":
                rankings,

            "metrics":
                metrics_by_method,

            "relevance":
                relevance,
        }

    for method in (
        "Dense",
        "RRF",
        "MMR",
        "Coverage",
    ):
        print_summary(
            method,
            stores[
                method
            ],
        )

    print()
    print(
        "=== Delta vs Dense ==="
    )

    for method in (
        "RRF",
        "MMR",
        "Coverage",
    ):

        print()
        print(
            method
        )

        for metric_name in (
            METRIC_NAMES
        ):

            delta = (
                mean(
                    stores[
                        method
                    ][
                        metric_name
                    ]
                )
                -
                mean(
                    stores[
                        "Dense"
                    ][
                        metric_name
                    ]
                )
            )

            print(
                f"  {metric_name}: "
                f"{delta:+.4f}"
            )

        print()
    print(
        "=== Results by Category ==="
    )

    categories = sorted(
        {
            example[
                "category"
            ]
            for example
            in queries
        }
    )

    for category in categories:

        print()
        print(
            category
        )

        for method in (
            "Dense",
            "RRF",
            "MMR",
            "Coverage",
        ):

            values = (
                category_stores[
                    method
                ][
                    category
                ]
            )

            print(
                f"  {method:<7} "
                f'R@3='
                f'{mean(values["Recall@3"]):.4f} '
                f'R@5='
                f'{mean(values["Recall@5"]):.4f} '
                f'R@10='
                f'{mean(values["Recall@10"]):.4f} '
                f'nDCG@3='
                f'{mean(values["nDCG@3"]):.4f}'
            )

    print()
    print(
        "=== Recovered Evidence Ranking ==="
    )

    retention = {
        method: {
            "top3": 0,
            "top5": 0,
            "top10": 0,
        }
        for method in (
            "RRF",
            "MMR",
            "Coverage",
        )
    }

    recovered_total = 0

    for query_id in sorted(
        KNOWN_CANDIDATE_FAILURES
    ):

        result = (
            diagnostics[
                query_id
            ]
        )

        relevant = (
            relevant_documents(
                result[
                    "relevance"
                ]
            )
        )

        dense_set = set(
            result[
                "rankings"
            ][
                "Dense"
            ]
        )

        union_set = set(
            result[
                "union_ids"
            ]
        )

        missing = (
            relevant
            - dense_set
        )

        recovered = (
            missing
            & union_set
        )

        print()
        print(
            f"{query_id}: "
            f"{result['query']}"
        )

        print(
            "  Missing from Dense: "
            f"{sorted(missing)}"
        )

        print(
            "  Recovered in union: "
            f"{sorted(recovered)}"
        )

        for document_id in sorted(
            recovered
        ):

            recovered_total += 1

            print(
                f"  {document_id}"
            )

            for method in (
                "RRF",
                "MMR",
                "Coverage",
            ):

                ranking = (
                    result[
                        "rankings"
                    ][
                        method
                    ]
                )

                rank = rank_of(
                    document_id,
                    ranking,
                )

                print(
                    f"    {method:<7}: "
                    f"{rank}"
                )

                if (
                    rank is not None
                    and rank <= 10
                ):
                    retention[
                        method
                    ][
                        "top10"
                    ] += 1

                if (
                    rank is not None
                    and rank <= 5
                ):
                    retention[
                        method
                    ][
                        "top5"
                    ] += 1

                if (
                    rank is not None
                    and rank <= 3
                ):
                    retention[
                        method
                    ][
                        "top3"
                    ] += 1

    print()
    print(
        "=== Recovered Evidence Retention ==="
    )

    print(
        f"Recovered documents: "
        f"{recovered_total}"
    )

    print()
    print(
        "=== Mechanism Diagnostics ==="
    )

    for method in (
        "Dense",
        "RRF",
        "MMR",
        "Coverage",
    ):

        coverage_at_5 = mean(
            mechanism_diagnostics[
                method
            ][
                "coverage_at_5"
            ]
        )

        pairwise_similarity_at_5 = mean(
            mechanism_diagnostics[
                method
            ][
                "pairwise_similarity_at_5"
            ]
        )

        print()
        print(
            method
        )

        print(
            "  Query Coverage@5: "
            f"{coverage_at_5:.4f}"
        )

        print(
            "  Mean Pairwise Similarity@5: "
            f"{pairwise_similarity_at_5:.4f}"
        )

    for method in (
        "RRF",
        "MMR",
        "Coverage",
    ):

        print(
            f"{method}: "
            f"top3="
            f'{retention[method]["top3"]}/'
            f"{recovered_total} "
            f"top5="
            f'{retention[method]["top5"]}/'
            f"{recovered_total} "
            f"top10="
            f'{retention[method]["top10"]}/'
            f"{recovered_total}"
        )


if __name__ == "__main__":
    main()

