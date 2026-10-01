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

SPOTCHECK_FILE = (
    EVALUATION_DIR
    / "rag_grounding_human_spotcheck_v1.json"
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
    / "rag_grounding_human_spotcheck_eval_v1.json"
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


def by_id(
    data: dict,
) -> dict:

    return {
        item[
            "annotation_id"
        ]:
            item
        for item
        in data.get(
            "items",
            []
        )
    }


def judge_label(
    item: dict,
) -> str:

    return (
        item[
            "judgment"
        ][
            "label"
        ]
    )


def main() -> None:

    spotcheck_data = load_json(
        SPOTCHECK_FILE
    )

    gemma = by_id(
        load_json(
            GEMMA_FILE
        )
    )

    qwen = by_id(
        load_json(
            QWEN_FILE
        )
    )

    spotchecks = (
        spotcheck_data.get(
            "items",
            []
        )
    )

    if not spotchecks:
        raise RuntimeError(
            "No human spot checks found."
        )

    incomplete = [
        item[
            "annotation_id"
        ]
        for item
        in spotchecks
        if (
            item.get(
                "human_label"
            )
            not in LABELS
        )
    ]

    if incomplete:
        raise RuntimeError(
            "Human annotation is "
            "incomplete: "
            f"{incomplete}"
        )

    gemma_correct = 0
    qwen_correct = 0

    judge_agreement_items = 0
    judge_disagreement_items = 0

    hidden_failures = 0

    human_counts = Counter()

    results = []

    print(
        "Experiment 014C — "
        "Human Grounding Audit"
    )

    print(
        f"Spot checks: "
        f"{len(spotchecks)}"
    )

    print()

    for item in spotchecks:

        item_id = (
            item[
                "annotation_id"
            ]
        )

        human = (
            item[
                "human_label"
            ]
        )

        gemma_label = (
            judge_label(
                gemma[
                    item_id
                ]
            )
        )

        qwen_label = (
            judge_label(
                qwen[
                    item_id
                ]
            )
        )

        human_counts[
            human
        ] += 1

        gemma_match = (
            gemma_label
            == human
        )

        qwen_match = (
            qwen_label
            == human
        )

        if gemma_match:
            gemma_correct += 1

        if qwen_match:
            qwen_correct += 1

        judges_agree = (
            gemma_label
            == qwen_label
        )

        if judges_agree:

            judge_agreement_items += 1

            if (
                human
                != gemma_label
            ):

                hidden_failures += 1

        else:

            judge_disagreement_items += 1

        result = {
            "annotation_id":
                item_id,

            "query_id":
                item[
                    "query_id"
                ],

            "claim_index":
                item[
                    "claim_index"
                ],

            "category":
                item[
                    "category"
                ],

            "claim":
                item[
                    "claim"
                ],

            "human":
                human,

            "human_note":
                item.get(
                    "human_note",
                    "",
                ),

            "gemma":
                gemma_label,

            "qwen_reasoning":
                qwen_label,

            "gemma_matches_human":
                gemma_match,

            "qwen_matches_human":
                qwen_match,

            "judges_agree":
                judges_agree,
        }

        results.append(
            result
        )

        print(
            item_id
        )

        print(
            f"  Human: "
            f"{human}"
        )

        print(
            f"  Gemma: "
            f"{gemma_label}"
        )

        print(
            f"  Qwen reasoning: "
            f"{qwen_label}"
        )

        if (
            item.get(
                "human_note"
            )
        ):

            print(
                "  Human note: "
                f"{item['human_note']}"
            )

        print()

    total = len(
        spotchecks
    )

    print(
        "=== Summary ==="
    )

    print()

    print(
        "Human labels:"
    )

    for label in LABELS:

        print(
            f"  {label:<7}: "
            f"{human_counts[label]}"
        )

    print()

    print(
        "Gemma ↔ human agreement: "
        f"{gemma_correct}/{total} "
        f"({gemma_correct / total:.4f})"
    )

    print(
        "Qwen ↔ human agreement: "
        f"{qwen_correct}/{total} "
        f"({qwen_correct / total:.4f})"
    )

    print()

    print(
        "Cross-judge disagreement "
        "items audited: "
        f"{judge_disagreement_items}"
    )

    print(
        "Cross-judge agreement "
        "items audited: "
        f"{judge_agreement_items}"
    )

    print()

    print(
        "Hidden judge-consensus failures:"
    )

    print(
        "  Cases where Gemma and Qwen "
        "agreed but human disagreed: "
        f"{hidden_failures}/"
        f"{judge_agreement_items}"
    )

    output = {
        "metadata": {
            "version":
                "v1",

            "important_note":
                (
                    "This is a targeted "
                    "human audit, not a "
                    "random population "
                    "estimate."
                ),
        },

        "summary": {
            "spot_checks":
                total,

            "human_labels":
                {
                    label:
                        human_counts[
                            label
                        ]
                    for label
                    in LABELS
                },

            "gemma_human_agreement":
                gemma_correct
                / total,

            "qwen_human_agreement":
                qwen_correct
                / total,

            "judge_disagreement_items":
                judge_disagreement_items,

            "judge_agreement_items":
                judge_agreement_items,

            "hidden_consensus_failures":
                hidden_failures,
        },

        "items":
            results,
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