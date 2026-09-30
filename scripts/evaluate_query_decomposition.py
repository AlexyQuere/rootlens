import json
from collections import defaultdict
from pathlib import Path

from sentence_transformers import (
    SentenceTransformer,
)

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

DECOMPOSITIONS_FILE = (
    BENCHMARK_DIR
    / "dev_decompositions_v3.json"
)


CANDIDATES_PER_QUERY = 10
RRF_K = 60

QUERY_INSTRUCTION = (
    "Represent this sentence for "
    "searching relevant passages: "
)


KNOWN_CANDIDATE_FAILURES = {
    "dev-008",
    "dev-015",
    "dev-020",
    "dev-021",
    "dev-022",
    "dev-023",
}


CANDIDATE_METHODS = (
    "Dense",
    "SemanticMatched",
    "Semantic",
    "Decomposition",
)


FINAL_METHODS = (
    "Dense",
    "SemanticMatchedRRF",
    "SemanticRRF",
    "DecompositionRRF",
)


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


def load_json(
    path: Path,
):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def build_mapping(
    data,
    field: str,
):

    return {
        item["query"]:
            item[field]
        for item in data["items"]
    }


def deduplicate_queries(
    queries,
):

    seen = set()
    result = []

    for query in queries:

        normalized = " ".join(
            query.lower().split()
        )

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        result.append(
            query
        )

    return result


def build_budget_matched_queries(
    original_query,
    frozen_rewrites,
    target_count,
):
    """Build a semantic-rewrite set with the same retrieval budget.

    target_count includes the original query.

    Frozen rewrites are consumed in their original order.
    No relevance-based selection is performed.
    """

    if target_count <= 0:
        raise ValueError(
            "target_count must be positive."
        )

    result = [
        original_query
    ]

    seen = {
        " ".join(
            original_query
            .lower()
            .split()
        )
    }

    for rewrite in frozen_rewrites:

        if (
            len(result)
            >= target_count
        ):
            break

        normalized = " ".join(
            rewrite.lower().split()
        )

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        result.append(
            rewrite
        )

    if (
        len(result)
        != target_count
    ):
        raise ValueError(
            "Could not construct a "
            "budget-matched semantic query "
            "set. "
            f"Target={target_count}, "
            f"obtained={len(result)}."
        )

    return result


def document_ids(
    ranking,
):

    return [
        document_id
        for document_id, _
        in ranking
    ]


def candidate_union(
    rankings,
):

    result = []
    seen = set()

    for ranking in rankings:

        for document_id, _ in ranking:

            if document_id in seen:
                continue

            seen.add(
                document_id
            )

            result.append(
                document_id
            )

    return result


def relevant_documents(
    relevance,
):

    return {
        document_id
        for document_id, grade
        in relevance.items()
        if grade > 0
    }


def candidate_recall(
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
            relevant
            & set(candidates)
        )
        / len(relevant)
    )


def oracle_ranking(
    candidate_ids,
    relevance,
):

    return sorted(
        candidate_ids,
        key=lambda document_id: (
            -relevance.get(
                document_id,
                0,
            ),
            document_id,
        ),
    )


def oracle_recall_at_3(
    candidates,
    relevance,
):

    ranking = oracle_ranking(
        candidates,
        relevance,
    )

    return recall_at_k(
        ranking,
        relevant_documents(
            relevance
        ),
        k=3,
    )


def oracle_ndcg_at_3(
    candidates,
    relevance,
):

    ranking = oracle_ranking(
        candidates,
        relevance,
    )

    return ndcg_at_k(
        ranking,
        relevance,
        k=3,
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


def mean_pairwise_query_similarity(
    model,
    queries,
):

    queries = (
        deduplicate_queries(
            queries
        )
    )

    if len(queries) < 2:
        return None

    encoded_queries = [
        QUERY_INSTRUCTION
        + query
        for query in queries
    ]

    embeddings = model.encode(
        encoded_queries,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    similarity_matrix = (
        embeddings
        @ embeddings.T
    )

    values = []

    for i in range(
        len(queries)
    ):
        for j in range(
            i + 1,
            len(queries),
        ):

            values.append(
                float(
                    similarity_matrix[
                        i,
                        j,
                    ]
                )
            )

    return mean(
        values
    )


def main():

    documents = (
        load_documents()
    )

    queries = load_json(
        DEV_FILE
    )

    rewrite_data = load_json(
        REWRITES_FILE
    )

    decomposition_data = load_json(
        DECOMPOSITIONS_FILE
    )

    validate_benchmark(
        documents,
        queries,
    )

    rewrite_mapping = (
        build_mapping(
            rewrite_data,
            "rewrites",
        )
    )

    decomposition_mapping = (
        build_mapping(
            decomposition_data,
            "decompositions",
        )
    )

    dense = DenseRetriever(
        documents,
        encoder=BGEEncoder(),
    )

    diversity_model = (
        SentenceTransformer(
            "BAAI/bge-small-en-v1.5"
        )
    )

    print(
        "Experiment 013 — "
        "Query Decomposition"
    )

    print(
        f"DEV only | "
        f"documents={len(documents)} "
        f"| queries={len(queries)}"
    )

    print()
    print(
        "Comparison:"
    )

    print(
        "  Dense"
    )

    print(
        "  SemanticMatched"
    )

    print(
        "  Semantic"
    )

    print(
        "  Decomposition"
    )

    #
    # Candidate-generation metrics.
    #
    candidate_stats = {
        method:
            defaultdict(list)
        for method in (
            CANDIDATE_METHODS
        )
    }

    #
    # Final-ranking metrics.
    #
    final_metrics = {
        method:
            defaultdict(list)
        for method in (
            FINAL_METHODS
        )
    }

    #
    # Candidate recall by category.
    #
    category_stats = {
        method:
            defaultdict(
                lambda:
                    defaultdict(
                        list
                    )
            )
        for method in (
            CANDIDATE_METHODS
        )
    }

    #
    # Query representation diagnostics.
    #
    semantic_query_similarity = []

    semantic_matched_query_similarity = []

    decomposition_query_similarity = []

    diversity_compared_queries = 0

    #
    # Query-level diagnostics.
    #
    diagnostics = {}

    for example in queries:

        query = (
            example[
                "query"
            ]
        )

        query_id = (
            example[
                "query_id"
            ]
        )

        category = (
            example[
                "category"
            ]
        )

        relevance = (
            example[
                "relevance"
            ]
        )

        #
        # Full semantic rewriting:
        # original + all 3 frozen rewrites.
        #
        semantic_queries = (
            deduplicate_queries(
                [
                    query,
                    *rewrite_mapping[
                        query
                    ],
                ]
            )
        )

        #
        # Decomposition:
        # original + 1–3 frozen subqueries.
        #
        decomposition_queries = (
            deduplicate_queries(
                [
                    query,
                    *decomposition_mapping[
                        query
                    ],
                ]
            )
        )

        #
        # Matched semantic control.
        #
        # It uses exactly the same number of
        # retrieval queries as the decomposition
        # after exact deduplication.
        #
        semantic_matched_queries = (
            build_budget_matched_queries(
                original_query=query,
                frozen_rewrites=(
                    rewrite_mapping[
                        query
                    ]
                ),
                target_count=len(
                    decomposition_queries
                ),
            )
        )

        #
        # Dense baseline.
        #
        dense_ranking = (
            dense.search(
                query,
                k=CANDIDATES_PER_QUERY,
            )
        )

        #
        # Full semantic rankings.
        #
        semantic_rankings = [
            dense.search(
                expanded_query,
                k=CANDIDATES_PER_QUERY,
            )
            for expanded_query
            in semantic_queries
        ]

        #
        # Budget-matched semantic rankings.
        #
        semantic_matched_rankings = [
            dense.search(
                expanded_query,
                k=CANDIDATES_PER_QUERY,
            )
            for expanded_query
            in semantic_matched_queries
        ]

        #
        # Decomposition rankings.
        #
        decomposition_rankings = [
            dense.search(
                expanded_query,
                k=CANDIDATES_PER_QUERY,
            )
            for expanded_query
            in decomposition_queries
        ]

        dense_candidates = (
            document_ids(
                dense_ranking
            )
        )

        semantic_candidates = (
            candidate_union(
                semantic_rankings
            )
        )

        semantic_matched_candidates = (
            candidate_union(
                semantic_matched_rankings
            )
        )

        decomposition_candidates = (
            candidate_union(
                decomposition_rankings
            )
        )

        candidate_sets = {
            "Dense":
                dense_candidates,

            "SemanticMatched":
                semantic_matched_candidates,

            "Semantic":
                semantic_candidates,

            "Decomposition":
                decomposition_candidates,
        }

        query_counts = {
            "Dense":
                1,

            "SemanticMatched":
                len(
                    semantic_matched_queries
                ),

            "Semantic":
                len(
                    semantic_queries
                ),

            "Decomposition":
                len(
                    decomposition_queries
                ),
        }

        #
        # Candidate-generation evaluation.
        #
        for (
            method,
            candidates,
        ) in candidate_sets.items():

            recall = (
                candidate_recall(
                    candidates,
                    relevance,
                )
            )

            oracle_r3 = (
                oracle_recall_at_3(
                    candidates,
                    relevance,
                )
            )

            oracle_ndcg3 = (
                oracle_ndcg_at_3(
                    candidates,
                    relevance,
                )
            )

            candidate_stats[
                method
            ][
                "candidate_recall"
            ].append(
                recall
            )

            candidate_stats[
                method
            ][
                "oracle_recall_3"
            ].append(
                oracle_r3
            )

            candidate_stats[
                method
            ][
                "oracle_ndcg_3"
            ].append(
                oracle_ndcg3
            )

            candidate_stats[
                method
            ][
                "union_size"
            ].append(
                len(candidates)
            )

            candidate_stats[
                method
            ][
                "query_count"
            ].append(
                query_counts[
                    method
                ]
            )

            category_stats[
                method
            ][
                category
            ][
                "candidate_recall"
            ].append(
                recall
            )

        #
        # RRF final-ranking diagnostic.
        #
        semantic_rrf = (
            reciprocal_rank_fusion(
                semantic_rankings,
                rrf_k=RRF_K,
            )
        )

        semantic_matched_rrf = (
            reciprocal_rank_fusion(
                semantic_matched_rankings,
                rrf_k=RRF_K,
            )
        )

        decomposition_rrf = (
            reciprocal_rank_fusion(
                decomposition_rankings,
                rrf_k=RRF_K,
            )
        )

        final_rankings = {
            "Dense":
                dense_candidates,

            "SemanticMatchedRRF":
                document_ids(
                    semantic_matched_rrf
                )[:10],

            "SemanticRRF":
                document_ids(
                    semantic_rrf
                )[:10],

            "DecompositionRRF":
                document_ids(
                    decomposition_rrf
                )[:10],
        }

        for (
            method,
            ranking,
        ) in final_rankings.items():

            metrics = compute_metrics(
                ranking,
                relevance,
            )

            for (
                metric_name,
                value,
            ) in metrics.items():

                final_metrics[
                    method
                ][
                    metric_name
                ].append(
                    value
                )

        #
        # Query-representation diversity.
        #
        semantic_similarity = (
            mean_pairwise_query_similarity(
                diversity_model,
                semantic_queries,
            )
        )

        if (
            semantic_similarity
            is not None
        ):
            semantic_query_similarity.append(
                semantic_similarity
            )

        #
        # For matched-vs-decomposition diversity,
        # only compare queries for which decomposition
        # actually contains more than one unique
        # retrieval query.
        #
        if (
            len(
                decomposition_queries
            )
            >= 2
        ):

            semantic_matched_similarity = (
                mean_pairwise_query_similarity(
                    diversity_model,
                    semantic_matched_queries,
                )
            )

            decomposition_similarity = (
                mean_pairwise_query_similarity(
                    diversity_model,
                    decomposition_queries,
                )
            )

            if (
                semantic_matched_similarity
                is None
                or decomposition_similarity
                is None
            ):
                raise RuntimeError(
                    "Expected pairwise query "
                    "similarity for the matched "
                    "comparison."
                )

            semantic_matched_query_similarity.append(
                semantic_matched_similarity
            )

            decomposition_query_similarity.append(
                decomposition_similarity
            )

            diversity_compared_queries += 1

        #
        # Save query-level diagnostics.
        #
        diagnostics[
            query_id
        ] = {
            "query":
                query,

            "relevance":
                relevance,

            "dense_candidates":
                dense_candidates,

            "semantic_matched_candidates":
                semantic_matched_candidates,

            "semantic_candidates":
                semantic_candidates,

            "decomposition_candidates":
                decomposition_candidates,

            "dense_query_count":
                1,

            "semantic_matched_query_count":
                len(
                    semantic_matched_queries
                ),

            "semantic_query_count":
                len(
                    semantic_queries
                ),

            "decomposition_query_count":
                len(
                    decomposition_queries
                ),
        }

    #
    # Candidate-generation summary.
    #
    print()
    print(
        "=== Candidate Generation ==="
    )

    for method in (
        CANDIDATE_METHODS
    ):

        values = (
            candidate_stats[
                method
            ]
        )

        print()
        print(
            method
        )

        print(
            "  Candidate Recall: "
            f'{mean(values["candidate_recall"]):.4f}'
        )

        print(
            "  Oracle Recall@3: "
            f'{mean(values["oracle_recall_3"]):.4f}'
        )

        print(
            "  Oracle nDCG@3: "
            f'{mean(values["oracle_ndcg_3"]):.4f}'
        )

        print(
            "  Mean union size: "
            f'{mean(values["union_size"]):.2f}'
        )

        print(
            "  Mean retrieval queries: "
            f'{mean(values["query_count"]):.2f}'
        )

    #
    # Budget sanity check.
    #
    semantic_matched_budget = mean(
        candidate_stats[
            "SemanticMatched"
        ][
            "query_count"
        ]
    )

    decomposition_budget = mean(
        candidate_stats[
            "Decomposition"
        ][
            "query_count"
        ]
    )

    print()
    print(
        "=== Retrieval Budget Check ==="
    )

    print(
        "SemanticMatched mean queries: "
        f"{semantic_matched_budget:.2f}"
    )

    print(
        "Decomposition mean queries: "
        f"{decomposition_budget:.2f}"
    )

    if (
        semantic_matched_budget
        != decomposition_budget
    ):
        raise RuntimeError(
            "SemanticMatched and "
            "Decomposition retrieval budgets "
            "do not match."
        )

    #
    # Query-representation diversity.
    #
    print()
    print(
        "=== Query Representation Diversity ==="
    )

    print(
        "Semantic full mean pairwise cosine: "
        f"{mean(semantic_query_similarity):.4f}"
    )

    print(
        "Budget-matched comparison queries: "
        f"{diversity_compared_queries}"
    )

    print(
        "SemanticMatched mean pairwise cosine: "
        f"{mean(semantic_matched_query_similarity):.4f}"
    )

    print(
        "Decomposition mean pairwise cosine: "
        f"{mean(decomposition_query_similarity):.4f}"
    )

    #
    # Candidate recall by category.
    #
    print()
    print(
        "=== Candidate Recall by Category ==="
    )

    categories = sorted(
        {
            example[
                "category"
            ]
            for example in queries
        }
    )

    for category in categories:

        print()
        print(
            category
        )

        for method in (
            CANDIDATE_METHODS
        ):

            values = (
                category_stats[
                    method
                ][
                    category
                ][
                    "candidate_recall"
                ]
            )

            print(
                f"  {method:<16} "
                f"{mean(values):.4f}"
            )

    #
    # RRF ranking diagnostic.
    #
    print()
    print(
        "=== Final Ranking Diagnostic ==="
    )

    for method in (
        FINAL_METHODS
    ):

        print()
        print(
            method
        )

        for metric_name in (
            METRIC_NAMES
        ):

            print(
                f"  {metric_name}: "
                f"{mean(final_metrics[method][metric_name]):.4f}"
            )

    #
    # Known candidate failures.
    #
    print()
    print(
        "=== Known Candidate Failures ==="
    )

    semantic_matched_recovered = 0
    semantic_recovered = 0
    decomposition_recovered = 0
    total_missing = 0

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
                "dense_candidates"
            ]
        )

        missing = (
            relevant
            - dense_set
        )

        semantic_matched_recovered_docs = (
            missing
            & set(
                result[
                    "semantic_matched_candidates"
                ]
            )
        )

        semantic_recovered_docs = (
            missing
            & set(
                result[
                    "semantic_candidates"
                ]
            )
        )

        decomposition_recovered_docs = (
            missing
            & set(
                result[
                    "decomposition_candidates"
                ]
            )
        )

        total_missing += len(
            missing
        )

        semantic_matched_recovered += len(
            semantic_matched_recovered_docs
        )

        semantic_recovered += len(
            semantic_recovered_docs
        )

        decomposition_recovered += len(
            decomposition_recovered_docs
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
            "  SemanticMatched recovered: "
            f"{sorted(semantic_matched_recovered_docs)}"
        )

        print(
            "  Semantic recovered: "
            f"{sorted(semantic_recovered_docs)}"
        )

        print(
            "  Decomposition recovered: "
            f"{sorted(decomposition_recovered_docs)}"
        )

    print()
    print(
        "Recovered known failures:"
    )

    print(
        "  SemanticMatched: "
        f"{semantic_matched_recovered}/"
        f"{total_missing}"
    )

    print(
        "  Semantic: "
        f"{semantic_recovered}/"
        f"{total_missing}"
    )

    print(
        "  Decomposition: "
        f"{decomposition_recovered}/"
        f"{total_missing}"
    )


if __name__ == "__main__":
    main()