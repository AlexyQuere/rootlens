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

GEMMA_FILE = (
    EVALUATION_DIR
    / "rag_grounding_judge_gemma_dev_v1.json"
)

QWEN_FILE = (
    EVALUATION_DIR
    / "rag_grounding_judge_qwen_reasoning_dev_v1.json"
)

OUTPUT_FILE = (
    EVALUATION_DIR
    / "rag_grounding_judge_agreement_v1.json"
)


LABELS = (
    "full",
    "partial",
    "none",
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


def items_by_id(
    data: dict,
) -> dict:

    items = data.get(
        "items",
        []
    )

    result = {}

    for item in items:

        annotation_id = (
            item[
                "annotation_id"
            ]
        )

        if annotation_id in result:
            raise RuntimeError(
                "Duplicate annotation ID: "
                f"{annotation_id}"
            )

        result[
            annotation_id
        ] = item

    return result


def label_of(
    item: dict,
) -> str:

    label = (
        item[
            "judgment"
        ][
            "label"
        ]
    )

    if label not in LABELS:
        raise RuntimeError(
            "Unexpected label: "
            f"{label}"
        )

    return label


def supporting_sources(
    item: dict,
) -> set[str]:

    return set(
        item[
            "judgment"
        ].get(
            "supporting_sources",
            [],
        )
    )


def jaccard(
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
        / len(union)
    )


def cohen_kappa(
    confusion: dict[
        str,
        dict[str, int],
    ],
    total: int,
) -> float | None:

    if total == 0:
        return None

    observed = (
        sum(
            confusion[
                label
            ][
                label
            ]
            for label
            in LABELS
        )
        / total
    )

    row_totals = {
        label:
            sum(
                confusion[
                    label
                ].values()
            )
        for label
        in LABELS
    }

    column_totals = {
        label:
            sum(
                confusion[
                    other
                ][
                    label
                ]
                for other
                in LABELS
            )
        for label
        in LABELS
    }

    expected = sum(
        (
            row_totals[
                label
            ]
            / total
        )
        * (
            column_totals[
                label
            ]
            / total
        )
        for label
        in LABELS
    )

    denominator = (
        1.0
        - expected
    )

    if abs(
        denominator
    ) < 1e-12:
        return None

    return (
        observed
        - expected
    ) / denominator


def main() -> None:

    gemma_data = load_json(
        GEMMA_FILE
    )

    qwen_data = load_json(
        QWEN_FILE
    )

    gemma = items_by_id(
        gemma_data
    )

    qwen = items_by_id(
        qwen_data
    )

    if set(
        gemma
    ) != set(
        qwen
    ):
        missing_from_gemma = (
            set(qwen)
            - set(gemma)
        )

        missing_from_qwen = (
            set(gemma)
            - set(qwen)
        )

        raise RuntimeError(
            "Judge artifacts contain "
            "different claims.\n"
            "Missing from Gemma: "
            f"{sorted(missing_from_gemma)}\n"
            "Missing from Qwen: "
            f"{sorted(missing_from_qwen)}"
        )

    annotation_ids = sorted(
        gemma
    )

    confusion = {
        gemma_label: {
            qwen_label: 0
            for qwen_label
            in LABELS
        }
        for gemma_label
        in LABELS
    }

    gemma_counts = Counter()
    qwen_counts = Counter()

    agreements = []
    disagreements = []

    source_jaccards = []

    for annotation_id in (
        annotation_ids
    ):

        gemma_item = (
            gemma[
                annotation_id
            ]
        )

        qwen_item = (
            qwen[
                annotation_id
            ]
        )

        #
        # Sanity checks: both judges must
        # evaluate exactly the same claim.
        #
        fields = (
            "query_id",
            "claim_index",
            "query",
            "claim",
        )

        for field in fields:

            if (
                gemma_item.get(
                    field
                )
                != qwen_item.get(
                    field
                )
            ):
                raise RuntimeError(
                    "Judge inputs differ "
                    f"for {annotation_id}, "
                    f"field={field}."
                )

        gemma_label = (
            label_of(
                gemma_item
            )
        )

        qwen_label = (
            label_of(
                qwen_item
            )
        )

        gemma_counts[
            gemma_label
        ] += 1

        qwen_counts[
            qwen_label
        ] += 1

        confusion[
            gemma_label
        ][
            qwen_label
        ] += 1

        gemma_sources = (
            supporting_sources(
                gemma_item
            )
        )

        qwen_sources = (
            supporting_sources(
                qwen_item
            )
        )

        source_similarity = (
            jaccard(
                gemma_sources,
                qwen_sources,
            )
        )

        source_jaccards.append(
            source_similarity
        )

        result = {
            "annotation_id":
                annotation_id,

            "query_id":
                gemma_item[
                    "query_id"
                ],

            "claim_index":
                gemma_item[
                    "claim_index"
                ],

            "category":
                gemma_item[
                    "category"
                ],

            "query":
                gemma_item[
                    "query"
                ],

            "claim":
                gemma_item[
                    "claim"
                ],

            "cited_sources":
                gemma_item[
                    "cited_sources"
                ],

            "gemma": {
                "label":
                    gemma_label,

                "supporting_sources":
                    sorted(
                        gemma_sources
                    ),

                "unsupported_part":
                    gemma_item[
                        "judgment"
                    ].get(
                        "unsupported_part"
                    ),

                "rationale":
                    gemma_item[
                        "judgment"
                    ][
                        "rationale"
                    ],
            },

            "qwen_reasoning": {
                "label":
                    qwen_label,

                "supporting_sources":
                    sorted(
                        qwen_sources
                    ),

                "unsupported_part":
                    qwen_item[
                        "judgment"
                    ].get(
                        "unsupported_part"
                    ),

                "rationale":
                    qwen_item[
                        "judgment"
                    ][
                        "rationale"
                    ],
            },

            "supporting_source_jaccard":
                source_similarity,
        }

        if (
            gemma_label
            == qwen_label
        ):

            agreements.append(
                result
            )

        else:

            disagreements.append(
                result
            )

    total = len(
        annotation_ids
    )

    agreement_count = len(
        agreements
    )

    disagreement_count = len(
        disagreements
    )

    agreement_rate = (
        agreement_count
        / total
    )

    kappa = (
        cohen_kappa(
            confusion=confusion,
            total=total,
        )
    )

    print(
        "Experiment 014C — "
        "Cross-Judge Agreement"
    )

    print(
        f"Claims: {total}"
    )

    print()

    print(
        "=== Label Distributions ==="
    )

    print()

    print(
        "Gemma"
    )

    for label in LABELS:

        print(
            f"  {label:<7} "
            f"{gemma_counts[label]}"
        )

    print()

    print(
        "Qwen reasoning-high"
    )

    for label in LABELS:

        print(
            f"  {label:<7} "
            f"{qwen_counts[label]}"
        )

    print()

    print(
        "=== Confusion Matrix ==="
    )

    print()

    print(
        "Gemma \\ Qwen"
    )

    print(
        "             "
        "full  partial  none"
    )

    for gemma_label in LABELS:

        values = [
            confusion[
                gemma_label
            ][
                qwen_label
            ]
            for qwen_label
            in LABELS
        ]

        print(
            f"{gemma_label:<11}"
            f"{values[0]:>5}"
            f"{values[1]:>9}"
            f"{values[2]:>6}"
        )

    print()

    print(
        "=== Agreement ==="
    )

    print(
        "Exact label agreement: "
        f"{agreement_count}/{total}"
    )

    print(
        "Agreement rate: "
        f"{agreement_rate:.4f}"
    )

    if kappa is None:

        print(
            "Cohen's kappa: N/A"
        )

    else:

        print(
            "Cohen's kappa: "
            f"{kappa:.4f}"
        )

    print(
        "Mean supporting-source "
        "Jaccard: "
        f"{mean(source_jaccards):.4f}"
    )

    print()

    print(
        "=== Disagreements ==="
    )

    if not disagreements:

        print(
            "No label disagreements."
        )

    for result in (
        disagreements
    ):

        print()
        print(
            result[
                "annotation_id"
            ]
        )

        print(
            "  category: "
            f"{result['category']}"
        )

        print(
            "  claim: "
            f"{result['claim']}"
        )

        print(
            "  cited sources: "
            + ", ".join(
                result[
                    "cited_sources"
                ]
            )
        )

        print(
            "  Gemma: "
            f"{result['gemma']['label']}"
        )

        if (
            result[
                "gemma"
            ][
                "unsupported_part"
            ]
        ):

            print(
                "    unsupported: "
                f"{result['gemma']['unsupported_part']}"
            )

        print(
            "    rationale: "
            f"{result['gemma']['rationale']}"
        )

        print(
            "  Qwen reasoning: "
            f"{result['qwen_reasoning']['label']}"
        )

        if (
            result[
                "qwen_reasoning"
            ][
                "unsupported_part"
            ]
        ):

            print(
                "    unsupported: "
                f"{result['qwen_reasoning']['unsupported_part']}"
            )

        print(
            "    rationale: "
            f"{result['qwen_reasoning']['rationale']}"
        )

    output = {
        "metadata": {
            "gemma_file":
                GEMMA_FILE.name,

            "qwen_file":
                QWEN_FILE.name,

            "claims":
                total,

            "important_note":
                (
                    "Neither judge is treated "
                    "as human ground truth."
                ),
        },

        "label_distributions": {
            "gemma":
                {
                    label:
                        gemma_counts[
                            label
                        ]
                    for label
                    in LABELS
                },

            "qwen_reasoning":
                {
                    label:
                        qwen_counts[
                            label
                        ]
                    for label
                    in LABELS
                },
        },

        "confusion_matrix":
            confusion,

        "agreement": {
            "count":
                agreement_count,

            "disagreements":
                disagreement_count,

            "rate":
                agreement_rate,

            "cohen_kappa":
                kappa,

            "mean_supporting_source_jaccard":
                mean(
                    source_jaccards
                ),
        },

        "disagreement_items":
            disagreements,
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
        "Saved agreement analysis to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()