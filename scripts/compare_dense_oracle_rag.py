from __future__ import annotations

import json
import statistics

from pathlib import Path

from rootlens.evaluation.failure_attribution import (
    citation_qrel_recall,
    recovered_evidence_uptake,
)
from rootlens.evaluation.failure_attribution import (
    EvidenceIntervention,
)


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

BASELINE_FILE = (
    BENCHMARK_DIR
    / "dev_rag_outputs_v1.json"
)

ORACLE_FILE = (
    EVALUATION_DIR
    / "rag_oracle_outputs_v1.json"
)

OUTPUT_FILE = (
    EVALUATION_DIR
    / "rag_failure_attribution_v1.json"
)


TARGET_QUERY_IDS = (
    "dev-008",
    "dev-015",
    "dev-020",
    "dev-021",
    "dev-022",
    "dev-023",
)


def load_json(
    path: Path,
):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def cited_sources(
    item: dict,
) -> set[str]:

    result = set()

    for claim in (
        item[
            "answer"
        ][
            "claims"
        ]
    ):

        result.update(
            claim[
                "sources"
            ]
        )

    return result


def print_answer(
    title: str,
    item: dict,
) -> None:

    print(
        f"  {title}:"
    )

    print(
        "    status: "
        f"{item['answer']['status']}"
    )

    claims = (
        item[
            "answer"
        ][
            "claims"
        ]
    )

    print(
        f"    claims: "
        f"{len(claims)}"
    )

    for index, claim in enumerate(
        claims,
        start=1,
    ):

        print(
            f"      {index}. "
            f"{claim['text']}"
        )

        print(
            "         sources: "
            + ", ".join(
                claim[
                    "sources"
                ]
            )
        )

    limitation = (
        item[
            "answer"
        ].get(
            "limitation"
        )
    )

    if limitation:

        print(
            "    limitation: "
            f"{limitation}"
        )


def main() -> None:

    queries = load_json(
        DEV_FILE
    )

    baseline_data = load_json(
        BASELINE_FILE
    )

    oracle_data = load_json(
        ORACLE_FILE
    )

    query_by_id = {
        item[
            "query_id"
        ]:
            item
        for item in queries
    }

    baseline_by_id = {
        item[
            "query_id"
        ]:
            item
        for item
        in baseline_data.get(
            "items",
            []
        )
    }

    oracle_by_id = {
        item[
            "query_id"
        ]:
            item
        for item
        in oracle_data.get(
            "items",
            []
        )
    }

    if (
        set(
            TARGET_QUERY_IDS
        )
        - set(
            oracle_by_id
        )
    ):
        raise RuntimeError(
            "Oracle output artifact "
            "is incomplete."
        )

    rows = []

    baseline_recalls = []
    oracle_recalls = []

    total_recovered = 0
    total_recovered_cited = 0

    print(
        "Experiment 014E — "
        "Dense vs Qrel-Enriched Context"
    )

    print(
        f"Queries: "
        f"{len(TARGET_QUERY_IDS)}"
    )

    print()

    for query_id in (
        TARGET_QUERY_IDS
    ):

        example = (
            query_by_id[
                query_id
            ]
        )

        baseline = (
            baseline_by_id[
                query_id
            ]
        )

        oracle = (
            oracle_by_id[
                query_id
            ]
        )

        intervention_data = (
            oracle[
                "intervention"
            ]
        )

        intervention = (
            EvidenceIntervention(
                baseline_ids=tuple(
                    intervention_data[
                        "baseline_ids"
                    ]
                ),

                enriched_ids=tuple(
                    intervention_data[
                        "enriched_ids"
                    ]
                ),

                positive_qrel_ids=tuple(
                    intervention_data[
                        "positive_qrel_ids"
                    ]
                ),

                recovered_qrel_ids=tuple(
                    intervention_data[
                        "recovered_qrel_ids"
                    ]
                ),

                dropped_baseline_ids=tuple(
                    intervention_data[
                        "dropped_baseline_ids"
                    ]
                ),

                omitted_positive_qrel_ids=tuple(
                    intervention_data[
                        "omitted_positive_qrel_ids"
                    ]
                ),
            )
        )

        baseline_cited = (
            cited_sources(
                baseline
            )
        )

        oracle_cited = (
            cited_sources(
                oracle
            )
        )

        relevance = (
            example[
                "relevance"
            ]
        )

        baseline_recall = (
            citation_qrel_recall(
                cited_sources=(
                    baseline_cited
                ),
                relevance=relevance,
            )
        )

        oracle_recall = (
            citation_qrel_recall(
                cited_sources=(
                    oracle_cited
                ),
                relevance=relevance,
            )
        )

        uptake = (
            recovered_evidence_uptake(
                cited_sources=(
                    oracle_cited
                ),
                intervention=(
                    intervention
                ),
            )
        )

        recovered = set(
            intervention
            .recovered_qrel_ids
        )

        recovered_cited = (
            recovered
            & oracle_cited
        )

        total_recovered += len(
            recovered
        )

        total_recovered_cited += len(
            recovered_cited
        )

        baseline_recalls.append(
            baseline_recall
        )

        oracle_recalls.append(
            oracle_recall
        )

        if not recovered:

            intervention_outcome = (
                "no_recovered_qrel"
            )

        elif recovered_cited:

            intervention_outcome = (
                "recovered_evidence_used"
            )

        else:

            intervention_outcome = (
                "recovered_evidence_not_cited"
            )

        row = {
            "query_id":
                query_id,

            "category":
                example[
                    "category"
                ],

            "question":
                example[
                    "query"
                ],

            "baseline_evidence":
                list(
                    intervention
                    .baseline_ids
                ),

            "enriched_evidence":
                list(
                    intervention
                    .enriched_ids
                ),

            "recovered_qrel":
                list(
                    intervention
                    .recovered_qrel_ids
                ),

            "dropped_baseline":
                list(
                    intervention
                    .dropped_baseline_ids
                ),

            "omitted_positive_qrel":
                list(
                    intervention
                    .omitted_positive_qrel_ids
                ),

            "baseline_status":
                baseline[
                    "answer"
                ][
                    "status"
                ],

            "oracle_status":
                oracle[
                    "answer"
                ][
                    "status"
                ],

            "baseline_claim_count":
                len(
                    baseline[
                        "answer"
                    ][
                        "claims"
                    ]
                ),

            "oracle_claim_count":
                len(
                    oracle[
                        "answer"
                    ][
                        "claims"
                    ]
                ),

            "baseline_cited_sources":
                sorted(
                    baseline_cited
                ),

            "oracle_cited_sources":
                sorted(
                    oracle_cited
                ),

            "baseline_qrel_citation_recall":
                baseline_recall,

            "oracle_qrel_citation_recall":
                oracle_recall,

            "citation_recall_delta":
                (
                    oracle_recall
                    - baseline_recall
                ),

            "recovered_evidence_uptake":
                uptake,

            "recovered_qrel_cited":
                sorted(
                    recovered_cited
                ),

            "intervention_outcome":
                intervention_outcome,
        }

        rows.append(
            row
        )

        print(
            "=" * 90
        )

        print(
            query_id
        )

        print(
            f"Question: "
            f"{example['query']}"
        )

        print()

        print(
            "Baseline evidence:"
        )

        print(
            "  "
            + ", ".join(
                intervention
                .baseline_ids
            )
        )

        print(
            "Qrel-enriched evidence:"
        )

        print(
            "  "
            + ", ".join(
                intervention
                .enriched_ids
            )
        )

        print(
            "Recovered qrel evidence:"
        )

        print(
            "  "
            + (
                ", ".join(
                    intervention
                    .recovered_qrel_ids
                )
                if (
                    intervention
                    .recovered_qrel_ids
                )
                else "[]"
            )
        )

        print()

        print(
            "Qrel citation recall: "
            f"{baseline_recall:.4f}"
            " -> "
            f"{oracle_recall:.4f}"
        )

        print(
            "Recovered evidence uptake: "
            + (
                f"{uptake:.4f}"
                if uptake is not None
                else "N/A"
            )
        )

        print(
            "Intervention outcome: "
            f"{intervention_outcome}"
        )

        print()

        print_answer(
            "DENSE BASELINE",
            baseline,
        )

        print()

        print_answer(
            "QREL-ENRICHED",
            oracle,
        )

        print()

    mean_baseline = (
        statistics.mean(
            baseline_recalls
        )
    )

    mean_oracle = (
        statistics.mean(
            oracle_recalls
        )
    )

    overall_uptake = (
        total_recovered_cited
        / total_recovered
        if total_recovered
        else None
    )

    print(
        "=" * 90
    )

    print(
        "=== Aggregate ==="
    )

    print(
        "Mean baseline qrel "
        "citation recall: "
        f"{mean_baseline:.4f}"
    )

    print(
        "Mean enriched qrel "
        "citation recall: "
        f"{mean_oracle:.4f}"
    )

    print(
        "Mean citation recall delta: "
        f"{mean_oracle - mean_baseline:+.4f}"
    )

    print(
        "Recovered qrel documents: "
        f"{total_recovered}"
    )

    print(
        "Recovered qrel documents cited: "
        f"{total_recovered_cited}"
    )

    print(
        "Overall recovered-evidence uptake: "
        + (
            f"{overall_uptake:.4f}"
            if overall_uptake is not None
            else "N/A"
        )
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "Qrel citation recall is not "
        "answer correctness or claim "
        "groundedness."
    )

    print(
        "Final failure attribution "
        "requires pairwise answer "
        "inspection."
    )

    output = {
        "metadata": {
            "experiment":
                "014E",

            "version":
                "v1",

            "baseline":
                BASELINE_FILE.name,

            "intervention":
                ORACLE_FILE.name,

            "important_note":
                (
                    "Qrel relevance is not "
                    "claim entailment. Final "
                    "attribution requires "
                    "answer-level inspection."
                ),
        },

        "aggregate": {
            "mean_baseline_qrel_citation_recall":
                mean_baseline,

            "mean_enriched_qrel_citation_recall":
                mean_oracle,

            "mean_citation_recall_delta":
                (
                    mean_oracle
                    - mean_baseline
                ),

            "recovered_qrel_documents":
                total_recovered,

            "recovered_qrel_documents_cited":
                total_recovered_cited,

            "recovered_evidence_uptake":
                overall_uptake,
        },

        "queries":
            rows,
    }

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