import json

from collections import defaultdict
from pathlib import Path

from rootlens.evaluation.rag_metrics import (
    compute_query_rag_metrics,
    validate_frozen_rag_item,
)


ROOT = Path(__file__).resolve().parents[1]

BENCHMARK_DIR = (
    ROOT
    / "data"
    / "benchmark_v2"
)

DEV_FILE = (
    BENCHMARK_DIR
    / "dev_queries.json"
)

OUTPUTS_FILE = (
    BENCHMARK_DIR
    / "dev_rag_outputs_v1.json"
)

RESULTS_FILE = (
    BENCHMARK_DIR
    / "dev_rag_eval_v1.json"
)


EXPECTED_DENSE_RECALL_AT_5 = (
    0.8299
)


def mean(
    values,
) -> float:

    values = list(
        values
    )

    if not values:
        return 0.0

    return (
        sum(values)
        / len(values)
    )


def mean_optional(
    values,
) -> float | None:

    filtered = [
        value
        for value in values
        if value is not None
    ]

    if not filtered:
        return None

    return mean(
        filtered
    )


def load_json(
    path: Path,
):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def format_optional(
    value: float | None,
) -> str:

    if value is None:
        return "N/A"

    return f"{value:.4f}"


def main() -> None:

    queries = load_json(
        DEV_FILE
    )

    frozen = load_json(
        OUTPUTS_FILE
    )

    items = frozen.get(
        "items",
        []
    )

    if (
        len(items)
        != len(queries)
    ):
        raise RuntimeError(
            "Frozen output count does "
            "not match DEV query count: "
            f"{len(items)} vs "
            f"{len(queries)}"
        )

    query_by_id = {
        example[
            "query_id"
        ]:
            example
        for example in queries
    }

    item_by_id = {
        item[
            "query_id"
        ]:
            item
        for item in items
    }

    if (
        set(query_by_id)
        != set(item_by_id)
    ):
        raise RuntimeError(
            "Frozen output query IDs "
            "do not match DEV query IDs."
        )

    status_counts = {
        "answered": 0,
        "partial": 0,
        "abstained": 0,
    }

    query_results = []

    category_results = (
        defaultdict(list)
    )

    retrieval_recalls = []

    citation_precisions = []

    citation_recalls = []

    evidence_retentions = []

    source_utilizations = []

    claim_counts = []

    sources_per_claim = []

    generation_attempts = []

    attempt_metadata_complete = (
        True
    )

    print(
        "Experiment 014B — "
        "Offline RAG Evaluation"
    )

    print(
        f"DEV only | "
        f"queries={len(queries)}"
    )

    print()

    for example in queries:

        query_id = (
            example[
                "query_id"
            ]
        )

        item = (
            item_by_id[
                query_id
            ]
        )

        validate_frozen_rag_item(
            item
        )

        if (
            item.get(
                "query"
            )
            != example[
                "query"
            ]
        ):
            raise RuntimeError(
                f"Query text mismatch "
                f"for {query_id}."
            )

        if (
            item.get(
                "category"
            )
            != example[
                "category"
            ]
        ):
            raise RuntimeError(
                f"Category mismatch "
                f"for {query_id}."
            )

        retrieved = [
            evidence[
                "source_id"
            ]
            for evidence
            in item[
                "evidence"
            ]
        ]

        answer = (
            item[
                "answer"
            ]
        )

        claims = (
            answer[
                "claims"
            ]
        )

        metrics = (
            compute_query_rag_metrics(
                relevance=(
                    example[
                        "relevance"
                    ]
                ),
                retrieved_source_ids=(
                    retrieved
                ),
                claims=claims,
            )
        )

        status = (
            answer[
                "status"
            ]
        )

        status_counts[
            status
        ] += 1

        retrieval_recalls.append(
            metrics
            .retrieval_qrel_recall
        )

        citation_precisions.append(
            metrics
            .citation_qrel_precision
        )

        citation_recalls.append(
            metrics
            .citation_qrel_recall
        )

        evidence_retentions.append(
            metrics
            .relevant_evidence_retention
        )

        source_utilizations.append(
            metrics
            .source_utilization
        )

        claim_counts.append(
            metrics
            .claim_count
        )

        sources_per_claim.append(
            metrics
            .mean_sources_per_claim
        )

        if (
            "generation_attempts"
            in item
        ):

            generation_attempts.append(
                item[
                    "generation_attempts"
                ]
            )

        else:

            attempt_metadata_complete = (
                False
            )

        result = {
            "query_id":
                query_id,

            "category":
                example[
                    "category"
                ],

            "status":
                status,

            "retrieval_qrel_recall":
                metrics
                .retrieval_qrel_recall,

            "citation_qrel_precision":
                metrics
                .citation_qrel_precision,

            "citation_qrel_recall":
                metrics
                .citation_qrel_recall,

            "relevant_evidence_retention":
                metrics
                .relevant_evidence_retention,

            "source_utilization":
                metrics
                .source_utilization,

            "claim_count":
                metrics
                .claim_count,

            "mean_sources_per_claim":
                metrics
                .mean_sources_per_claim,

            "missing_relevant_from_retrieval":
                list(
                    metrics
                    .missing_relevant_from_retrieval
                ),

            "retrieved_relevant_not_cited":
                list(
                    metrics
                    .retrieved_relevant_not_cited
                ),

            "cited_qrel_irrelevant":
                list(
                    metrics
                    .cited_qrel_irrelevant
                ),
        }

        query_results.append(
            result
        )

        category_results[
            example[
                "category"
            ]
        ].append(
            result
        )

    aggregate = {
        "retrieval_qrel_recall":
            mean(
                retrieval_recalls
            ),

        "citation_qrel_precision":
            mean_optional(
                citation_precisions
            ),

        "citation_qrel_recall":
            mean(
                citation_recalls
            ),

        "relevant_evidence_retention":
            mean_optional(
                evidence_retentions
            ),

        "source_utilization":
            mean(
                source_utilizations
            ),

        "mean_claims_per_query":
            mean(
                claim_counts
            ),

        "mean_sources_per_claim":
            mean(
                sources_per_claim
            ),

        "status_counts":
            status_counts,
    }

    print(
        "=== Aggregate ==="
    )

    print(
        "Retrieval qrel recall: "
        f"{aggregate['retrieval_qrel_recall']:.4f}"
    )

    print(
        "Citation qrel precision: "
        f"{format_optional(aggregate['citation_qrel_precision'])}"
    )

    print(
        "Citation qrel recall: "
        f"{aggregate['citation_qrel_recall']:.4f}"
    )

    print(
        "Relevant evidence retention: "
        f"{format_optional(aggregate['relevant_evidence_retention'])}"
    )

    print(
        "Source utilization: "
        f"{aggregate['source_utilization']:.4f}"
    )

    print(
        "Mean claims/query: "
        f"{aggregate['mean_claims_per_query']:.2f}"
    )

    print(
        "Mean sources/claim: "
        f"{aggregate['mean_sources_per_claim']:.2f}"
    )

    print()

    print(
        "Status distribution:"
    )

    for status in (
        "answered",
        "partial",
        "abstained",
    ):

        print(
            f"  {status}: "
            f"{status_counts[status]}"
        )

    print()

    print(
        "=== Retrieval Sanity Check ==="
    )

    actual_recall = (
        aggregate[
            "retrieval_qrel_recall"
        ]
    )

    print(
        "Expected Dense Recall@5 "
        "from previous experiments: "
        f"{EXPECTED_DENSE_RECALL_AT_5:.4f}"
    )

    print(
        "Frozen RAG retrieval recall: "
        f"{actual_recall:.4f}"
    )

    if (
        abs(
            actual_recall
            - EXPECTED_DENSE_RECALL_AT_5
        )
        > 0.001
    ):

        raise RuntimeError(
            "RAG retrieval does not "
            "reproduce the previous "
            "Dense Recall@5 baseline."
        )

    print(
        "Sanity check: PASS"
    )

    print()

    print(
        "=== By Category ==="
    )

    category_summary = {}

    for category in sorted(
        category_results
    ):

        values = (
            category_results[
                category
            ]
        )

        summary = {
            "queries":
                len(values),

            "retrieval_qrel_recall":
                mean(
                    item[
                        "retrieval_qrel_recall"
                    ]
                    for item in values
                ),

            "citation_qrel_precision":
                mean_optional(
                    item[
                        "citation_qrel_precision"
                    ]
                    for item in values
                ),

            "citation_qrel_recall":
                mean(
                    item[
                        "citation_qrel_recall"
                    ]
                    for item in values
                ),

            "mean_claims":
                mean(
                    item[
                        "claim_count"
                    ]
                    for item in values
                ),
        }

        category_summary[
            category
        ] = summary

        print()
        print(
            category
        )

        print(
            "  Retrieval recall: "
            f"{summary['retrieval_qrel_recall']:.4f}"
        )

        print(
            "  Citation precision: "
            f"{format_optional(summary['citation_qrel_precision'])}"
        )

        print(
            "  Citation recall: "
            f"{summary['citation_qrel_recall']:.4f}"
        )

        print(
            "  Mean claims: "
            f"{summary['mean_claims']:.2f}"
        )

    print()

    print(
        "=== Evidence Diagnostics ==="
    )

    for result in (
        query_results
    ):

        has_diagnostic = any(
            (
                result[
                    "missing_relevant_from_retrieval"
                ],
                result[
                    "retrieved_relevant_not_cited"
                ],
                result[
                    "cited_qrel_irrelevant"
                ],
            )
        )

        if not has_diagnostic:
            continue

        print()
        print(
            result[
                "query_id"
            ]
        )

        print(
            "  Missing relevant "
            "from retrieval: "
            f"{result['missing_relevant_from_retrieval']}"
        )

        print(
            "  Retrieved relevant "
            "but not cited: "
            f"{result['retrieved_relevant_not_cited']}"
        )

        print(
            "  Cited but qrel-irrelevant: "
            f"{result['cited_qrel_irrelevant']}"
        )

    print()

    print(
        "=== Schema Retry Metadata ==="
    )

    if (
        attempt_metadata_complete
    ):

        retry_count = sum(
            attempts > 1
            for attempts
            in generation_attempts
        )

        print(
            "generation_attempts "
            "available for all queries."
        )

        print(
            "Queries requiring retry: "
            f"{retry_count}/"
            f"{len(generation_attempts)}"
        )

        print(
            "Mean generation attempts: "
            f"{mean(generation_attempts):.3f}"
        )

    else:

        print(
            "generation_attempts metadata "
            "is incomplete."
        )

        print(
            "Retry-rate metrics will not "
            "be interpreted for this "
            "frozen artifact."
        )

    results = {
        "metadata": {
            "source_outputs":
                OUTPUTS_FILE.name,

            "queries":
                len(queries),

            "attempt_metadata_complete":
                attempt_metadata_complete,
        },

        "aggregate":
            aggregate,

        "categories":
            category_summary,

        "queries":
            query_results,
    }

    RESULTS_FILE.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "Saved evaluation to:"
    )

    print(
        RESULTS_FILE
    )


if __name__ == "__main__":
    main()