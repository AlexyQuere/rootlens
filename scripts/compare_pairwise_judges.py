from __future__ import annotations

import json

from collections import Counter
from pathlib import Path

from rootlens.evaluation.pairwise_metrics import (
    cohen_kappa,
    confusion_matrix,
    consensus_label,
    exact_agreement,
    non_tie_rate,
    preference_counts,
)


ROOT = Path(__file__).resolve().parents[1]

EVALUATION_DIR = (
    ROOT
    / "data"
    / "evaluation"
)

GEMMA_FILE = (
    EVALUATION_DIR
    / "rag_pairwise_gemma_v1.json"
)

QWEN_FILE = (
    EVALUATION_DIR
    / "rag_pairwise_qwen_reasoning_v1.json"
)

DETERMINISTIC_FILE = (
    EVALUATION_DIR
    / "rag_dense_vs_semantic_v1.json"
)

OUTPUT_FILE = (
    EVALUATION_DIR
    / "rag_pairwise_judge_agreement_v1.json"
)


def load_json(
    path: Path,
):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def by_id(
    artifact: dict,
) -> dict[str, dict]:

    return {
        item[
            "query_id"
        ]:
            item
        for item
        in artifact.get(
            "items",
            []
        )
    }


def print_counts(
    title: str,
    values: list[str],
) -> None:

    counts = (
        preference_counts(
            values
        )
    )

    print(
        title
    )

    print(
        f"  Dense:    "
        f"{counts['dense']}"
    )

    print(
        f"  Semantic: "
        f"{counts['semantic']}"
    )

    print(
        f"  Tie:      "
        f"{counts['tie']}"
    )


def consensus_counts(
    rows: list[dict],
) -> dict[str, int]:

    counts = Counter(
        row[
            "consensus"
        ]
        for row
        in rows
    )

    return {
        "dense":
            counts[
                "dense"
            ],

        "semantic":
            counts[
                "semantic"
            ],

        "tie":
            counts[
                "tie"
            ],

        "disagreement":
            counts[
                "disagreement"
            ],
    }


def main() -> None:

    gemma = load_json(
        GEMMA_FILE
    )

    qwen = load_json(
        QWEN_FILE
    )

    deterministic = load_json(
        DETERMINISTIC_FILE
    )

    gemma_meta = (
        gemma.get(
            "metadata",
            {}
        )
    )

    qwen_meta = (
        qwen.get(
            "metadata",
            {}
        )
    )

    if (
        gemma_meta.get(
            "order"
        )
        == qwen_meta.get(
            "order"
        )
    ):

        raise RuntimeError(
            "The two judges must use "
            "opposite answer orders."
        )

    if (
        gemma_meta.get(
            "system_identity_visible_to_judge"
        )
        is not False
    ):

        raise RuntimeError(
            "Gemma run was not blind."
        )

    if (
        qwen_meta.get(
            "system_identity_visible_to_judge"
        )
        is not False
    ):

        raise RuntimeError(
            "Qwen run was not blind."
        )

    gemma_items = by_id(
        gemma
    )

    qwen_items = by_id(
        qwen
    )

    deterministic_items = {
        item[
            "query_id"
        ]:
            item
        for item
        in deterministic.get(
            "queries",
            []
        )
    }

    ids = sorted(
        gemma_items
    )

    if (
        set(ids)
        != set(
            qwen_items
        )
    ):

        raise RuntimeError(
            "Judge query IDs do not match."
        )

    if len(ids) != 24:

        raise RuntimeError(
            "Expected 24 pairwise judgments."
        )

    missing_deterministic = (
        set(ids)
        - set(
            deterministic_items
        )
    )

    if missing_deterministic:

        raise RuntimeError(
            "Missing deterministic "
            "comparison rows: "
            f"{sorted(missing_deterministic)}"
        )

    rows = []

    for query_id in ids:

        gemma_item = (
            gemma_items[
                query_id
            ]
        )

        qwen_item = (
            qwen_items[
                query_id
            ]
        )

        deterministic_item = (
            deterministic_items[
                query_id
            ]
        )

        if (
            gemma_item[
                "context_changed"
            ]
            != qwen_item[
                "context_changed"
            ]
        ):

            raise RuntimeError(
                "Context-change metadata "
                f"differs for {query_id}."
            )

        context_changed = (
            gemma_item[
                "context_changed"
            ]
        )

        expected_context_changed = (
            set(
                deterministic_item[
                    "dense_evidence"
                ]
            )
            !=
            set(
                deterministic_item[
                    "semantic_evidence"
                ]
            )
        )

        if (
            context_changed
            != expected_context_changed
        ):

            raise RuntimeError(
                "Pairwise context metadata "
                "does not match deterministic "
                f"comparison for {query_id}."
            )

        gemma_preference = (
            gemma_item[
                "preferred_system"
            ]
        )

        qwen_preference = (
            qwen_item[
                "preferred_system"
            ]
        )

        consensus = (
            consensus_label(
                gemma_preference,
                qwen_preference,
            )
        )

        delta = (
            deterministic_item[
                "delta"
            ]
        )

        rows.append(
            {
                "query_id":
                    query_id,

                "category":
                    gemma_item[
                        "category"
                    ],

                "context_changed":
                    context_changed,

                "gemma_preference":
                    gemma_preference,

                "qwen_preference":
                    qwen_preference,

                "consensus":
                    consensus,

                "gemma_raw_winner":
                    gemma_item[
                        "winner"
                    ],

                "qwen_raw_winner":
                    qwen_item[
                        "winner"
                    ],

                "gemma_rationale":
                    gemma_item[
                        "rationale"
                    ],

                "qwen_rationale":
                    qwen_item[
                        "rationale"
                    ],

                "retrieval_recall_delta":
                    delta[
                        "retrieval_qrel_recall"
                    ],

                "citation_precision_delta":
                    delta[
                        "citation_qrel_precision"
                    ],

                "citation_recall_delta":
                    delta[
                        "citation_qrel_recall"
                    ],

                "evidence_jaccard":
                    deterministic_item[
                        "evidence_jaccard"
                    ],
            }
        )

    gemma_preferences = [
        row[
            "gemma_preference"
        ]
        for row
        in rows
    ]

    qwen_preferences = [
        row[
            "qwen_preference"
        ]
        for row
        in rows
    ]

    agreement = (
        exact_agreement(
            gemma_preferences,
            qwen_preferences,
        )
    )

    kappa = (
        cohen_kappa(
            gemma_preferences,
            qwen_preferences,
        )
    )

    matrix = (
        confusion_matrix(
            gemma_preferences,
            qwen_preferences,
        )
    )

    changed_rows = [
        row
        for row
        in rows
        if row[
            "context_changed"
        ]
    ]

    control_rows = [
        row
        for row
        in rows
        if not row[
            "context_changed"
        ]
    ]

    if len(
        changed_rows
    ) != 15:

        raise RuntimeError(
            "Expected 15 changed-context "
            f"queries, got {len(changed_rows)}."
        )

    if len(
        control_rows
    ) != 9:

        raise RuntimeError(
            "Expected 9 identical-context "
            f"controls, got {len(control_rows)}."
        )

    print(
        "Experiment 014F — "
        "Cross-Judge Analysis"
    )

    print()

    print(
        "Gemma model: "
        f"{gemma_meta.get('judge_model')}"
    )

    print(
        "Qwen model: "
        f"{qwen_meta.get('judge_model')}"
    )

    print(
        "Gemma order: "
        f"{gemma_meta.get('order')}"
    )

    print(
        "Qwen order: "
        f"{qwen_meta.get('order')}"
    )

    print()

    print(
        "=== Overall Preferences ==="
    )

    print_counts(
        "Gemma:",
        gemma_preferences,
    )

    print_counts(
        "Qwen:",
        qwen_preferences,
    )

    print()

    agreement_count = sum(
        left == right
        for left, right
        in zip(
            gemma_preferences,
            qwen_preferences,
        )
    )

    print(
        "=== Cross-Judge Agreement ==="
    )

    print(
        "Exact agreement: "
        f"{agreement_count}/24 "
        f"({agreement:.4f})"
    )

    if kappa is None:

        print(
            "Cohen kappa: N/A"
        )

    else:

        print(
            "Cohen kappa: "
            f"{kappa:.4f}"
        )

    print()

    print(
        "Confusion matrix "
        "(Gemma rows / Qwen columns)"
    )

    print(
        "                 dense  "
        "semantic  tie"
    )

    for label in (
        "dense",
        "semantic",
        "tie",
    ):

        print(
            f"{label:<10}"
            f"{matrix[label]['dense']:>10}"
            f"{matrix[label]['semantic']:>10}"
            f"{matrix[label]['tie']:>6}"
        )

    print()

    print(
        "=== Raw Position Choices ==="
    )

    gemma_positions = Counter(
        item[
            "winner"
        ]
        for item
        in gemma_items.values()
    )

    qwen_positions = Counter(
        item[
            "winner"
        ]
        for item
        in qwen_items.values()
    )

    print(
        "Gemma A/B/tie: "
        f"{gemma_positions['A']}/"
        f"{gemma_positions['B']}/"
        f"{gemma_positions['tie']}"
    )

    print(
        "Qwen A/B/tie: "
        f"{qwen_positions['A']}/"
        f"{qwen_positions['B']}/"
        f"{qwen_positions['tie']}"
    )

    print()

    print(
        "=== Changed Context ==="
    )

    print(
        f"Queries: "
        f"{len(changed_rows)}"
    )

    changed_gemma = [
        row[
            "gemma_preference"
        ]
        for row
        in changed_rows
    ]

    changed_qwen = [
        row[
            "qwen_preference"
        ]
        for row
        in changed_rows
    ]

    print_counts(
        "Gemma:",
        changed_gemma,
    )

    print_counts(
        "Qwen:",
        changed_qwen,
    )

    changed_consensus = (
        consensus_counts(
            changed_rows
        )
    )

    print(
        "Consensus:"
    )

    for label in (
        "dense",
        "semantic",
        "tie",
        "disagreement",
    ):

        print(
            f"  {label}: "
            f"{changed_consensus[label]}"
        )

    print()

    print(
        "=== Identical-Context "
        "Negative Control ==="
    )

    print(
        f"Queries: "
        f"{len(control_rows)}"
    )

    control_gemma = [
        row[
            "gemma_preference"
        ]
        for row
        in control_rows
    ]

    control_qwen = [
        row[
            "qwen_preference"
        ]
        for row
        in control_rows
    ]

    print_counts(
        "Gemma:",
        control_gemma,
    )

    print_counts(
        "Qwen:",
        control_qwen,
    )

    print(
        "Gemma non-tie rate: "
        f"{non_tie_rate(control_gemma):.4f}"
    )

    print(
        "Qwen non-tie rate: "
        f"{non_tie_rate(control_qwen):.4f}"
    )

    control_consensus = (
        consensus_counts(
            control_rows
        )
    )

    print(
        "Consensus:"
    )

    for label in (
        "dense",
        "semantic",
        "tie",
        "disagreement",
    ):

        print(
            f"  {label}: "
            f"{control_consensus[label]}"
        )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "Non-tie preferences on "
        "identical-context controls "
        "cannot be attributed to the "
        "retrieval method."
    )

    print()

    print(
        "=== Changed-Context "
        "Consensus Non-Ties ==="
    )

    changed_non_ties = [
        row
        for row
        in changed_rows
        if row[
            "consensus"
        ]
        in (
            "dense",
            "semantic",
        )
    ]

    if not changed_non_ties:

        print(
            "None."
        )

    else:

        for row in changed_non_ties:

            print(
                f"{row['query_id']}: "
                f"{row['consensus']}"
            )

            print(
                "  retrieval recall delta: "
                f"{row['retrieval_recall_delta']:+.4f}"
            )

            print(
                "  citation precision delta: "
                f"{row['citation_precision_delta']:+.4f}"
            )

            print(
                "  citation recall delta: "
                f"{row['citation_recall_delta']:+.4f}"
            )

            print(
                "  evidence Jaccard: "
                f"{row['evidence_jaccard']:.4f}"
            )

    print()

    print(
        "=== Judge Disagreements ==="
    )

    disagreements = [
        row
        for row
        in rows
        if row[
            "consensus"
        ]
        == "disagreement"
    ]

    if not disagreements:

        print(
            "None."
        )

    else:

        for row in disagreements:

            print(
                f"{row['query_id']}: "
                f"Gemma="
                f"{row['gemma_preference']} | "
                f"Qwen="
                f"{row['qwen_preference']} | "
                f"context_changed="
                f"{row['context_changed']}"
            )

    print()

    print(
        "=== Human Audit Candidates ==="
    )

    audit_reasons: dict[
        str,
        set[str],
    ] = {}

    for row in rows:

        reasons = set()

        if (
            row[
                "consensus"
            ]
            == "disagreement"
        ):

            reasons.add(
                "cross_judge_disagreement"
            )

        if (
            not row[
                "context_changed"
            ]
            and (
                row[
                    "gemma_preference"
                ]
                != "tie"
                or row[
                    "qwen_preference"
                ]
                != "tie"
            )
        ):

            reasons.add(
                "negative_control_non_tie"
            )

        if (
            row[
                "context_changed"
            ]
            and row[
                "consensus"
            ]
            in (
                "dense",
                "semantic",
            )
        ):

            reasons.add(
                "changed_context_consensus_win"
            )

        if reasons:

            audit_reasons[
                row[
                    "query_id"
                ]
            ] = reasons

    if not audit_reasons:

        print(
            "No targeted audit "
            "candidates."
        )

    else:

        for query_id in sorted(
            audit_reasons
        ):

            print(
                f"{query_id}: "
                + ", ".join(
                    sorted(
                        audit_reasons[
                            query_id
                        ]
                    )
                )
            )

    output = {
        "metadata": {
            "experiment":
                "014F",

            "evaluation":
                "cross_judge_pairwise",

            "gemma_model":
                gemma_meta.get(
                    "judge_model"
                ),

            "qwen_model":
                qwen_meta.get(
                    "judge_model"
                ),

            "gemma_order":
                gemma_meta.get(
                    "order"
                ),

            "qwen_order":
                qwen_meta.get(
                    "order"
                ),

            "negative_control_definition":
                (
                    "Dense and Semantic "
                    "retrieval produced the "
                    "same top-5 evidence set."
                ),
        },

        "overall": {
            "gemma_preferences":
                preference_counts(
                    gemma_preferences
                ),

            "qwen_preferences":
                preference_counts(
                    qwen_preferences
                ),

            "exact_agreement_count":
                agreement_count,

            "exact_agreement":
                agreement,

            "cohen_kappa":
                kappa,

            "confusion_matrix":
                matrix,
        },

        "changed_context": {
            "query_count":
                len(
                    changed_rows
                ),

            "gemma_preferences":
                preference_counts(
                    changed_gemma
                ),

            "qwen_preferences":
                preference_counts(
                    changed_qwen
                ),

            "consensus":
                changed_consensus,
        },

        "negative_control": {
            "query_count":
                len(
                    control_rows
                ),

            "gemma_preferences":
                preference_counts(
                    control_gemma
                ),

            "qwen_preferences":
                preference_counts(
                    control_qwen
                ),

            "gemma_non_tie_rate":
                non_tie_rate(
                    control_gemma
                ),

            "qwen_non_tie_rate":
                non_tie_rate(
                    control_qwen
                ),

            "consensus":
                control_consensus,
        },

        "audit_candidates": {
            query_id:
                sorted(
                    reasons
                )
            for query_id, reasons
            in sorted(
                audit_reasons.items()
            )
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
        "Saved analysis to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()