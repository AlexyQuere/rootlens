from __future__ import annotations

import json

from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EVALUATION_DIR = (
    ROOT
    / "data"
    / "evaluation"
)

AUDIT_FILE = (
    EVALUATION_DIR
    / "rag_pairwise_human_audit_v1.json"
)

KEY_FILE = (
    EVALUATION_DIR
    / "rag_pairwise_human_audit_key_v1.json"
)

AGREEMENT_FILE = (
    EVALUATION_DIR
    / "rag_pairwise_judge_agreement_v1.json"
)

LEGACY_AGREEMENT_FILE = (
    EVALUATION_DIR
    / "rag_pairwise_judge_agreement_v1.js"
)

OUTPUT_FILE = (
    EVALUATION_DIR
    / "rag_pairwise_human_audit_eval_v1.json"
)


VALID_SYSTEM_LABELS = {
    "dense",
    "semantic",
    "tie",
    "inconclusive",
}


def load_json(
    path: Path,
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def resolve_agreement_file() -> Path:

    if AGREEMENT_FILE.exists():
        return AGREEMENT_FILE

    if LEGACY_AGREEMENT_FILE.exists():

        print(
            "WARNING: using legacy .js "
            "agreement artifact."
        )

        return LEGACY_AGREEMENT_FILE

    raise FileNotFoundError(
        "Could not find pairwise judge "
        "agreement artifact."
    )


def map_human_label(
    raw_label: str,
    key: dict,
) -> str:

    if raw_label == "tie":
        return "tie"

    if raw_label == "inconclusive":
        return "inconclusive"

    if raw_label == "A":

        return key[
            "answer_a_system"
        ]

    if raw_label == "B":

        return key[
            "answer_b_system"
        ]

    raise ValueError(
        "Invalid human label: "
        f"{raw_label}"
    )


def counts(
    labels: list[str],
) -> dict[str, int]:

    counter = Counter(
        labels
    )

    return {
        label:
            counter[label]
        for label
        in (
            "dense",
            "semantic",
            "tie",
            "inconclusive",
        )
    }


def print_counts(
    title: str,
    labels: list[str],
) -> None:

    result = counts(
        labels
    )

    print(
        title
    )

    print(
        f"  Dense:        "
        f"{result['dense']}"
    )

    print(
        f"  Semantic:     "
        f"{result['semantic']}"
    )

    print(
        f"  Tie:          "
        f"{result['tie']}"
    )

    print(
        f"  Inconclusive: "
        f"{result['inconclusive']}"
    )


def main() -> None:

    audit = load_json(
        AUDIT_FILE
    )

    key = load_json(
        KEY_FILE
    )

    agreement_path = (
        resolve_agreement_file()
    )

    agreement = load_json(
        agreement_path
    )

    audit_items = {
        item[
            "query_id"
        ]:
            item
        for item
        in audit[
            "items"
        ]
    }

    key_items = {
        item[
            "query_id"
        ]:
            item
        for item
        in key[
            "items"
        ]
    }

    agreement_items = {
        item[
            "query_id"
        ]:
            item
        for item
        in agreement[
            "queries"
        ]
    }

    if (
        set(
            audit_items
        )
        != set(
            key_items
        )
    ):

        raise RuntimeError(
            "Audit and blind-key "
            "query IDs do not match."
        )

    if len(
        audit_items
    ) != 15:

        raise RuntimeError(
            "Expected 15 audited "
            f"queries, got "
            f"{len(audit_items)}."
        )

    audited_rows = []

    for query_id in sorted(
        audit_items
    ):

        audit_item = (
            audit_items[
                query_id
            ]
        )

        key_item = (
            key_items[
                query_id
            ]
        )

        agreement_item = (
            agreement_items[
                query_id
            ]
        )

        raw_label = (
            audit_item.get(
                "human_label"
            )
        )

        if raw_label is None:

            raise RuntimeError(
                "Human audit is incomplete: "
                f"{query_id}"
            )

        human_label = (
            map_human_label(
                raw_label,
                key_item,
            )
        )

        if (
            human_label
            not in VALID_SYSTEM_LABELS
        ):

            raise RuntimeError(
                "Invalid mapped "
                "human label."
            )

        audited_rows.append(
            {
                "query_id":
                    query_id,

                "context_changed":
                    agreement_item[
                        "context_changed"
                    ],

                "audit_reasons":
                    key_item[
                        "audit_reasons"
                    ],

                "human_raw_label":
                    raw_label,

                "human_preference":
                    human_label,

                "human_rationale":
                    audit_item.get(
                        "human_rationale"
                    ),

                "gemma_preference":
                    agreement_item[
                        "gemma_preference"
                    ],

                "qwen_preference":
                    agreement_item[
                        "qwen_preference"
                    ],

                "judge_consensus":
                    agreement_item[
                        "consensus"
                    ],

                "retrieval_recall_delta":
                    agreement_item[
                        "retrieval_recall_delta"
                    ],

                "citation_precision_delta":
                    agreement_item[
                        "citation_precision_delta"
                    ],

                "citation_recall_delta":
                    agreement_item[
                        "citation_recall_delta"
                    ],

                "evidence_jaccard":
                    agreement_item[
                        "evidence_jaccard"
                    ],
            }
        )

    print(
        "Experiment 014F — "
        "Human Audit Evaluation"
    )

    print()

    print(
        "Audited queries: "
        f"{len(audited_rows)}"
    )

    print(
        "Human audit was targeted, "
        "not a random sample."
    )

    print()

    all_human = [
        row[
            "human_preference"
        ]
        for row
        in audited_rows
    ]

    print_counts(
        "=== Human Preferences "
        "(15 targeted cases) ===",
        all_human,
    )

    changed_audited = [
        row
        for row
        in audited_rows
        if row[
            "context_changed"
        ]
    ]

    control_audited = [
        row
        for row
        in audited_rows
        if not row[
            "context_changed"
        ]
    ]

    print()

    print_counts(
        "=== Audited Changed-Context "
        "Cases ===",
        [
            row[
                "human_preference"
            ]
            for row
            in changed_audited
        ],
    )

    print()

    print_counts(
        "=== Audited Identical-Context "
        "Controls ===",
        [
            row[
                "human_preference"
            ]
            for row
            in control_audited
        ],
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "Any Dense/Semantic preference "
        "on an identical-context control "
        "cannot be attributed to retrieval."
    )

    #
    # Human vs each judge
    #

    comparable_rows = [
        row
        for row
        in audited_rows
        if row[
            "human_preference"
        ]
        != "inconclusive"
    ]

    gemma_matches = sum(
        row[
            "human_preference"
        ]
        == row[
            "gemma_preference"
        ]
        for row
        in comparable_rows
    )

    qwen_matches = sum(
        row[
            "human_preference"
        ]
        == row[
            "qwen_preference"
        ]
        for row
        in comparable_rows
    )

    print()

    print(
        "=== Human ↔ Judge Agreement ==="
    )

    print(
        "Comparable human labels: "
        f"{len(comparable_rows)}"
    )

    if comparable_rows:

        print(
            "Gemma agreement: "
            f"{gemma_matches}/"
            f"{len(comparable_rows)} "
            f"("
            f"{gemma_matches / len(comparable_rows):.4f}"
            f")"
        )

        print(
            "Qwen agreement: "
            f"{qwen_matches}/"
            f"{len(comparable_rows)} "
            f"("
            f"{qwen_matches / len(comparable_rows):.4f}"
            f")"
        )

    #
    # Check consensus wins
    #

    consensus_win_rows = [
        row
        for row
        in audited_rows
        if (
            "changed_context_consensus_win"
            in row[
                "audit_reasons"
            ]
        )
    ]

    consensus_confirmed = 0

    print()

    print(
        "=== Changed-Context "
        "Consensus Wins ==="
    )

    for row in consensus_win_rows:

        judges = (
            row[
                "judge_consensus"
            ]
        )

        human = (
            row[
                "human_preference"
            ]
        )

        confirmed = (
            judges == human
        )

        if confirmed:
            consensus_confirmed += 1

        print(
            f"{row['query_id']}: "
            f"judges={judges} | "
            f"human={human} | "
            f"confirmed={confirmed}"
        )

        print(
            "  retrieval recall delta: "
            f"{row['retrieval_recall_delta']:+.4f}"
        )

        print(
            "  citation recall delta: "
            f"{row['citation_recall_delta']:+.4f}"
        )

    print()

    print(
        "Consensus wins confirmed "
        "by human audit: "
        f"{consensus_confirmed}/"
        f"{len(consensus_win_rows)}"
    )

    #
    # Resolve judge disagreements
    #

    disagreement_rows = [
        row
        for row
        in audited_rows
        if (
            "cross_judge_disagreement"
            in row[
                "audit_reasons"
            ]
        )
    ]

    print()

    print(
        "=== Cross-Judge "
        "Disagreements Resolved "
        "by Human Audit ==="
    )

    for row in disagreement_rows:

        print(
            f"{row['query_id']}: "
            f"Gemma="
            f"{row['gemma_preference']} | "
            f"Qwen="
            f"{row['qwen_preference']} | "
            f"Human="
            f"{row['human_preference']} | "
            f"context_changed="
            f"{row['context_changed']}"
        )

    #
    # Negative-control noise
    #

    negative_control_rows = [
        row
        for row
        in audited_rows
        if (
            "negative_control_non_tie"
            in row[
                "audit_reasons"
            ]
        )
    ]

    print()

    print(
        "=== Negative-Control "
        "Non-Ties ==="
    )

    for row in negative_control_rows:

        print(
            f"{row['query_id']}: "
            f"Gemma="
            f"{row['gemma_preference']} | "
            f"Qwen="
            f"{row['qwen_preference']} | "
            f"Human="
            f"{row['human_preference']}"
        )

    #
    # Full 24-query combined adjudication.
    #
    # Human labels override judge results for
    # every audited query.
    #
    # Non-audited cases are kept only when the
    # two judges already agreed.
    #

    human_by_id = {
        row[
            "query_id"
        ]:
            row[
                "human_preference"
            ]
        for row
        in audited_rows
    }

    final_rows = []

    for query_id in sorted(
        agreement_items
    ):

        row = (
            agreement_items[
                query_id
            ]
        )

        if query_id in human_by_id:

            final_label = (
                human_by_id[
                    query_id
                ]
            )

            source = (
                "human_audit"
            )

        else:

            consensus = (
                row[
                    "consensus"
                ]
            )

            if (
                consensus
                == "disagreement"
            ):

                raise RuntimeError(
                    "Unaudited judge "
                    "disagreement found for "
                    f"{query_id}."
                )

            final_label = (
                consensus
            )

            source = (
                "judge_consensus"
            )

        final_rows.append(
            {
                "query_id":
                    query_id,

                "context_changed":
                    row[
                        "context_changed"
                    ],

                "final_label":
                    final_label,

                "adjudication_source":
                    source,
            }
        )

    if len(
        final_rows
    ) != 24:

        raise RuntimeError(
            "Expected 24 final "
            "adjudications."
        )

    changed_final = [
        row[
            "final_label"
        ]
        for row
        in final_rows
        if row[
            "context_changed"
        ]
    ]

    control_final = [
        row[
            "final_label"
        ]
        for row
        in final_rows
        if not row[
            "context_changed"
        ]
    ]

    all_final = [
        row[
            "final_label"
        ]
        for row
        in final_rows
    ]

    print()

    print(
        "=" * 72
    )

    print(
        "=== FINAL COMBINED "
        "ADJUDICATION ==="
    )

    print(
        "=" * 72
    )

    print()

    print_counts(
        "All 24 queries:",
        all_final,
    )

    print()

    print_counts(
        "15 changed-context queries:",
        changed_final,
    )

    print()

    print_counts(
        "9 identical-context controls:",
        control_final,
    )

    print()

    print(
        "Interpretation:"
    )

    print(
        "- Changed-context preferences "
        "may reflect retrieval effects."
    )

    print(
        "- Identical-context preferences "
        "measure generation/evaluation "
        "variability, not retrieval."
    )

    print(
        "- This targeted audit should not "
        "be reported as a population "
        "accuracy estimate."
    )

    output = {
        "metadata": {
            "experiment":
                "014F",

            "evaluation":
                "targeted_human_pairwise_audit",

            "version":
                "v1",

            "audited_queries":
                len(
                    audited_rows
                ),

            "audit_sampling":
                (
                    "targeted: judge "
                    "disagreements, negative-"
                    "control non-ties, and "
                    "changed-context consensus "
                    "wins"
                ),

            "important_note":
                (
                    "Human audit is used for "
                    "targeted adjudication, "
                    "not as a random-sample "
                    "estimate of answer quality."
                ),
        },

        "human_targeted_counts":
            counts(
                all_human
            ),

        "human_changed_context_counts":
            counts(
                [
                    row[
                        "human_preference"
                    ]
                    for row
                    in changed_audited
                ]
            ),

        "human_negative_control_counts":
            counts(
                [
                    row[
                        "human_preference"
                    ]
                    for row
                    in control_audited
                ]
            ),

        "human_judge_agreement": {
            "comparable_labels":
                len(
                    comparable_rows
                ),

            "gemma_matches":
                gemma_matches,

            "qwen_matches":
                qwen_matches,

            "gemma_rate":
                (
                    gemma_matches
                    / len(
                        comparable_rows
                    )
                    if comparable_rows
                    else None
                ),

            "qwen_rate":
                (
                    qwen_matches
                    / len(
                        comparable_rows
                    )
                    if comparable_rows
                    else None
                ),
        },

        "consensus_wins": {
            "count":
                len(
                    consensus_win_rows
                ),

            "human_confirmed":
                consensus_confirmed,
        },

        "final_combined_adjudication": {
            "all_24":
                counts(
                    all_final
                ),

            "changed_context_15":
                counts(
                    changed_final
                ),

            "negative_control_9":
                counts(
                    control_final
                ),
        },

        "audited_queries":
            audited_rows,

        "final_queries":
            final_rows,
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
        "Saved evaluation to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()