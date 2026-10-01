from __future__ import annotations

import json
import statistics

from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BENCHMARK_DIR = (
    ROOT
    / "data"
    / "benchmark_v2"
)

EVALUATION_DIR = (
    ROOT
    / "data"
    / "evaluation"
)

DEV_FILE = (
    BENCHMARK_DIR
    / "dev_queries.json"
)

DENSE_FILE = (
    BENCHMARK_DIR
    / "dev_rag_outputs_v1.json"
)

SEMANTIC_FILE = (
    BENCHMARK_DIR
    / "dev_rag_outputs_semantic_v1.json"
)

OUTPUT_FILE = (
    EVALUATION_DIR
    / "rag_dense_vs_semantic_v1.json"
)


def load_json(
    path: Path,
):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def mean(
    values: list[float],
) -> float:

    if not values:
        return 0.0

    return statistics.mean(
        values
    )


def positive_qrels(
    relevance: dict[
        str,
        int,
    ],
) -> set[str]:

    return {
        source_id
        for source_id, grade
        in relevance.items()
        if grade > 0
    }


def evidence_ids(
    item: dict,
) -> list[str]:

    return [
        evidence[
            "source_id"
        ]
        for evidence
        in item[
            "evidence"
        ]
    ]


def cited_sources(
    item: dict,
) -> set[str]:

    cited = set()

    for claim in (
        item[
            "answer"
        ][
            "claims"
        ]
    ):

        cited.update(
            claim[
                "sources"
            ]
        )

    return cited


def retrieval_qrel_recall(
    retrieved: set[str],
    relevant: set[str],
) -> float:

    if not relevant:
        return 0.0

    return (
        len(
            retrieved
            & relevant
        )
        / len(
            relevant
        )
    )


def citation_qrel_precision(
    cited: set[str],
    relevant: set[str],
) -> float:

    if not cited:
        return 0.0

    return (
        len(
            cited
            & relevant
        )
        / len(
            cited
        )
    )


def citation_qrel_recall(
    cited: set[str],
    relevant: set[str],
) -> float:

    if not relevant:
        return 0.0

    return (
        len(
            cited
            & relevant
        )
        / len(
            relevant
        )
    )


def relevant_evidence_retention(
    retrieved: set[str],
    cited: set[str],
    relevant: set[str],
) -> float:

    retrieved_relevant = (
        retrieved
        & relevant
    )

    if not retrieved_relevant:
        return 0.0

    return (
        len(
            cited
            & retrieved_relevant
        )
        / len(
            retrieved_relevant
        )
    )


def source_utilization(
    retrieved: set[str],
    cited: set[str],
) -> float:

    if not retrieved:
        return 0.0

    return (
        len(
            cited
            & retrieved
        )
        / len(
            retrieved
        )
    )


def set_jaccard(
    left: set[str],
    right: set[str],
) -> float:

    union = (
        left
        | right
    )

    if not union:
        return 1.0

    return (
        len(
            left
            & right
        )
        / len(
            union
        )
    )


def compute_metrics(
    item: dict,
    relevance: dict[
        str,
        int,
    ],
) -> dict[str, float]:

    relevant = (
        positive_qrels(
            relevance
        )
    )

    retrieved = set(
        evidence_ids(
            item
        )
    )

    cited = (
        cited_sources(
            item
        )
    )

    return {
        "retrieval_qrel_recall":
            retrieval_qrel_recall(
                retrieved,
                relevant,
            ),

        "citation_qrel_precision":
            citation_qrel_precision(
                cited,
                relevant,
            ),

        "citation_qrel_recall":
            citation_qrel_recall(
                cited,
                relevant,
            ),

        "relevant_evidence_retention":
            relevant_evidence_retention(
                retrieved,
                cited,
                relevant,
            ),

        "source_utilization":
            source_utilization(
                retrieved,
                cited,
            ),

        "claim_count":
            float(
                len(
                    item[
                        "answer"
                    ][
                        "claims"
                    ]
                )
            ),
    }


def main() -> None:

    queries = load_json(
        DEV_FILE
    )

    dense_data = load_json(
        DENSE_FILE
    )

    semantic_data = load_json(
        SEMANTIC_FILE
    )

    if not isinstance(
        queries,
        list,
    ):
        raise RuntimeError(
            "DEV benchmark must "
            "be a JSON list."
        )

    query_by_id = {
        item[
            "query_id"
        ]:
            item
        for item
        in queries
    }

    dense_items = {
        item[
            "query_id"
        ]:
            item
        for item
        in dense_data.get(
            "items",
            []
        )
    }

    semantic_items = {
        item[
            "query_id"
        ]:
            item
        for item
        in semantic_data.get(
            "items",
            []
        )
    }

    ids = set(
        query_by_id
    )

    if (
        ids
        != set(
            dense_items
        )
        or ids
        != set(
            semantic_items
        )
    ):
        raise RuntimeError(
            "DEV, Dense and Semantic "
            "query IDs do not match."
        )

    if len(ids) != 24:
        raise RuntimeError(
            "Expected 24 DEV queries."
        )

    metric_names = (
        "retrieval_qrel_recall",
        "citation_qrel_precision",
        "citation_qrel_recall",
        "relevant_evidence_retention",
        "source_utilization",
        "claim_count",
    )

    dense_store = {
        name: []
        for name
        in metric_names
    }

    semantic_store = {
        name: []
        for name
        in metric_names
    }

    category_store = defaultdict(
        lambda: {
            "dense_retrieval_recall": [],
            "semantic_retrieval_recall": [],
            "dense_citation_recall": [],
            "semantic_citation_recall": [],
        }
    )

    rows = []

    dense_latencies = []

    semantic_rag_latencies = []

    semantic_retrieval_latencies = []

    semantic_attempts = []

    changed_context_count = 0

    semantic_relevant_added = 0

    semantic_relevant_lost = 0

    print(
        "Experiment 014F — "
        "Dense vs Semantic RAG"
    )

    print(
        f"Queries: {len(ids)}"
    )

    print()

    for query in queries:

        query_id = (
            query[
                "query_id"
            ]
        )

        category = (
            query[
                "category"
            ]
        )

        relevance = (
            query[
                "relevance"
            ]
        )

        relevant = (
            positive_qrels(
                relevance
            )
        )

        dense = (
            dense_items[
                query_id
            ]
        )

        semantic = (
            semantic_items[
                query_id
            ]
        )

        dense_metrics = (
            compute_metrics(
                dense,
                relevance,
            )
        )

        semantic_metrics = (
            compute_metrics(
                semantic,
                relevance,
            )
        )

        for name in metric_names:

            dense_store[
                name
            ].append(
                dense_metrics[
                    name
                ]
            )

            semantic_store[
                name
            ].append(
                semantic_metrics[
                    name
                ]
            )

        category_store[
            category
        ][
            "dense_retrieval_recall"
        ].append(
            dense_metrics[
                "retrieval_qrel_recall"
            ]
        )

        category_store[
            category
        ][
            "semantic_retrieval_recall"
        ].append(
            semantic_metrics[
                "retrieval_qrel_recall"
            ]
        )

        category_store[
            category
        ][
            "dense_citation_recall"
        ].append(
            dense_metrics[
                "citation_qrel_recall"
            ]
        )

        category_store[
            category
        ][
            "semantic_citation_recall"
        ].append(
            semantic_metrics[
                "citation_qrel_recall"
            ]
        )

        dense_evidence = set(
            evidence_ids(
                dense
            )
        )

        semantic_evidence = set(
            evidence_ids(
                semantic
            )
        )

        added = (
            semantic_evidence
            - dense_evidence
        )

        dropped = (
            dense_evidence
            - semantic_evidence
        )

        added_relevant = (
            added
            & relevant
        )

        dropped_relevant = (
            dropped
            & relevant
        )

        semantic_relevant_added += (
            len(
                added_relevant
            )
        )

        semantic_relevant_lost += (
            len(
                dropped_relevant
            )
        )

        if (
            dense_evidence
            != semantic_evidence
        ):
            changed_context_count += 1

        dense_cited = (
            cited_sources(
                dense
            )
        )

        semantic_cited = (
            cited_sources(
                semantic
            )
        )

        dense_latency = (
            dense.get(
                "latency_ms"
            )
        )

        semantic_rag_latency = (
            semantic.get(
                "rag_latency_ms"
            )
        )

        semantic_retrieval_latency = (
            semantic.get(
                "retrieval_latency_ms"
            )
        )

        if isinstance(
            dense_latency,
            (int, float),
        ):
            dense_latencies.append(
                float(
                    dense_latency
                )
            )

        if isinstance(
            semantic_rag_latency,
            (int, float),
        ):
            semantic_rag_latencies.append(
                float(
                    semantic_rag_latency
                )
            )

        if isinstance(
            semantic_retrieval_latency,
            (int, float),
        ):
            semantic_retrieval_latencies.append(
                float(
                    semantic_retrieval_latency
                )
            )

        attempts = (
            semantic.get(
                "generation_attempts"
            )
        )

        if isinstance(
            attempts,
            int,
        ):
            semantic_attempts.append(
                attempts
            )

        row = {
            "query_id":
                query_id,

            "category":
                category,

            "question":
                query[
                    "query"
                ],

            "dense_evidence":
                evidence_ids(
                    dense
                ),

            "semantic_evidence":
                evidence_ids(
                    semantic
                ),

            "evidence_jaccard":
                set_jaccard(
                    dense_evidence,
                    semantic_evidence,
                ),

            "semantic_added":
                sorted(
                    added
                ),

            "semantic_dropped":
                sorted(
                    dropped
                ),

            "semantic_added_relevant":
                sorted(
                    added_relevant
                ),

            "semantic_dropped_relevant":
                sorted(
                    dropped_relevant
                ),

            "dense_cited_sources":
                sorted(
                    dense_cited
                ),

            "semantic_cited_sources":
                sorted(
                    semantic_cited
                ),

            "dense_status":
                dense[
                    "answer"
                ][
                    "status"
                ],

            "semantic_status":
                semantic[
                    "answer"
                ][
                    "status"
                ],

            "dense_metrics":
                dense_metrics,

            "semantic_metrics":
                semantic_metrics,

            "delta": {
                name:
                    (
                        semantic_metrics[
                            name
                        ]
                        - dense_metrics[
                            name
                        ]
                    )
                for name
                in metric_names
            },
        }

        rows.append(
            row
        )

    aggregate = {}

    print(
        "=== Aggregate Metrics ==="
    )

    for name in metric_names:

        dense_value = mean(
            dense_store[
                name
            ]
        )

        semantic_value = mean(
            semantic_store[
                name
            ]
        )

        delta = (
            semantic_value
            - dense_value
        )

        aggregate[
            name
        ] = {
            "dense":
                dense_value,

            "semantic":
                semantic_value,

            "delta":
                delta,
        }

        print(
            f"{name}:"
        )

        print(
            f"  Dense:    "
            f"{dense_value:.4f}"
        )

        print(
            f"  Semantic: "
            f"{semantic_value:.4f}"
        )

        print(
            f"  Delta:    "
            f"{delta:+.4f}"
        )

    print()

    print(
        "=== Evidence Composition ==="
    )

    print(
        "Queries with changed top-5 set: "
        f"{changed_context_count}/24"
    )

    print(
        "Relevant docs added by Semantic: "
        f"{semantic_relevant_added}"
    )

    print(
        "Relevant docs lost by Semantic: "
        f"{semantic_relevant_lost}"
    )

    mean_jaccard = mean(
        [
            row[
                "evidence_jaccard"
            ]
            for row
            in rows
        ]
    )

    print(
        "Mean top-5 evidence Jaccard: "
        f"{mean_jaccard:.4f}"
    )

    print()

    print(
        "=== By Category ==="
    )

    category_output = {}

    for category in sorted(
        category_store
    ):

        values = (
            category_store[
                category
            ]
        )

        dense_retrieval = mean(
            values[
                "dense_retrieval_recall"
            ]
        )

        semantic_retrieval = mean(
            values[
                "semantic_retrieval_recall"
            ]
        )

        dense_citation = mean(
            values[
                "dense_citation_recall"
            ]
        )

        semantic_citation = mean(
            values[
                "semantic_citation_recall"
            ]
        )

        category_output[
            category
        ] = {
            "dense_retrieval_recall":
                dense_retrieval,

            "semantic_retrieval_recall":
                semantic_retrieval,

            "dense_citation_recall":
                dense_citation,

            "semantic_citation_recall":
                semantic_citation,
        }

        print(
            f"{category}"
        )

        print(
            "  retrieval recall: "
            f"{dense_retrieval:.4f}"
            " -> "
            f"{semantic_retrieval:.4f}"
        )

        print(
            "  citation recall:  "
            f"{dense_citation:.4f}"
            " -> "
            f"{semantic_citation:.4f}"
        )

    print()

    print(
        "=== Retrieval / Runtime Cost ==="
    )

    print(
        "Dense retrieval queries/question: "
        "1"
    )

    print(
        "Semantic retrieval queries/question: "
        "4"
    )

    if semantic_retrieval_latencies:

        print(
            "Semantic retrieval latency_ms:"
        )

        print(
            "  mean: "
            f"{mean(semantic_retrieval_latencies):.1f}"
        )

        print(
            "  median: "
            f"{statistics.median(semantic_retrieval_latencies):.1f}"
        )

    if (
        dense_latencies
        and semantic_rag_latencies
        and len(
            dense_latencies
        )
        == len(
            semantic_rag_latencies
        )
    ):

        dense_latency_mean = mean(
            dense_latencies
        )

        semantic_latency_mean = mean(
            semantic_rag_latencies
        )

        latency_delta = (
            semantic_latency_mean
            - dense_latency_mean
        )

        print(
            "Mean end-to-end RAG latency_ms:"
        )

        print(
            "  Dense:    "
            f"{dense_latency_mean:.1f}"
        )

        print(
            "  Semantic: "
            f"{semantic_latency_mean:.1f}"
        )

        print(
            "  Delta:    "
            f"{latency_delta:+.1f}"
        )

    else:

        dense_latency_mean = None
        semantic_latency_mean = (
            mean(
                semantic_rag_latencies
            )
            if semantic_rag_latencies
            else None
        )

        latency_delta = None

        print(
            "Dense vs Semantic latency "
            "not directly comparable from "
            "available artifacts."
        )

    if semantic_attempts:

        retry_count = sum(
            attempts > 1
            for attempts
            in semantic_attempts
        )

        print(
            "Semantic schema retries: "
            f"{retry_count}/"
            f"{len(semantic_attempts)}"
        )

        print(
            "Semantic mean generation "
            "attempts: "
            f"{mean([float(x) for x in semantic_attempts]):.3f}"
        )

    else:

        retry_count = None

    print()

    print(
        "=== Largest Retrieval Changes ==="
    )

    sorted_rows = sorted(
        rows,
        key=lambda row: (
            -abs(
                row[
                    "delta"
                ][
                    "retrieval_qrel_recall"
                ]
            ),
            row[
                "query_id"
            ],
        ),
    )

    for row in sorted_rows:

        retrieval_delta = (
            row[
                "delta"
            ][
                "retrieval_qrel_recall"
            ]
        )

        citation_delta = (
            row[
                "delta"
            ][
                "citation_qrel_recall"
            ]
        )

        if (
            retrieval_delta == 0.0
            and citation_delta == 0.0
            and not row[
                "semantic_added"
            ]
        ):
            continue

        print(
            f"{row['query_id']}: "
            f"retrieval "
            f"{retrieval_delta:+.4f} | "
            f"citation "
            f"{citation_delta:+.4f}"
        )

        print(
            "  added: "
            + (
                ", ".join(
                    row[
                        "semantic_added"
                    ]
                )
                if row[
                    "semantic_added"
                ]
                else "[]"
            )
        )

        print(
            "  dropped: "
            + (
                ", ".join(
                    row[
                        "semantic_dropped"
                    ]
                )
                if row[
                    "semantic_dropped"
                ]
                else "[]"
            )
        )

    output = {
        "metadata": {
            "experiment":
                "014F",

            "version":
                "v1",

            "comparison":
                "Dense vs Semantic Multi-Query RRF",

            "dense_file":
                DENSE_FILE.name,

            "semantic_file":
                SEMANTIC_FILE.name,

            "context_budget":
                5,

            "dense_retrieval_queries_per_question":
                1,

            "semantic_retrieval_queries_per_question":
                4,

            "important_note":
                (
                    "Qrel metrics measure benchmark "
                    "relevance, not answer correctness "
                    "or claim entailment."
                ),
        },

        "aggregate":
            aggregate,

        "evidence_composition": {
            "changed_context_queries":
                changed_context_count,

            "relevant_docs_added":
                semantic_relevant_added,

            "relevant_docs_lost":
                semantic_relevant_lost,

            "mean_evidence_jaccard":
                mean_jaccard,
        },

        "runtime": {
            "dense_mean_rag_latency_ms":
                dense_latency_mean,

            "semantic_mean_rag_latency_ms":
                semantic_latency_mean,

            "rag_latency_delta_ms":
                latency_delta,

            "semantic_mean_retrieval_latency_ms":
                (
                    mean(
                        semantic_retrieval_latencies
                    )
                    if semantic_retrieval_latencies
                    else None
                ),

            "semantic_schema_retry_count":
                retry_count,
        },

        "by_category":
            category_output,

        "queries":
            rows,
    }

    EVALUATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()

    print(
        "Saved comparison to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()