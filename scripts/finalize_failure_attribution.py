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

INPUT_FILE = (
    EVALUATION_DIR
    / "rag_failure_attribution_v1.json"
)

OUTPUT_FILE = (
    EVALUATION_DIR
    / "rag_failure_attribution_final_v1.json"
)


ATTRIBUTIONS = {
    "dev-008": {
        "label":
            "retrieval_gap_not_answer_limiting",

        "material_answer_improvement":
            False,

        "reason":
            (
                "The Dense baseline already explains "
                "that HTTP 500 is a propagated symptom "
                "that does not identify the backend "
                "root cause. The recovered incident "
                "response evidence adds investigation "
                "guidance but does not repair a "
                "deficient answer."
            ),
    },

    "dev-015": {
        "label":
            "retrieval_gap_not_answer_limiting",

        "material_answer_improvement":
            False,

        "reason":
            (
                "The Dense baseline already provides "
                "the decisive diagnostic distinction: "
                "missing Payment server span indicates "
                "failure before reaching PaymentService, "
                "while a server span indicates an "
                "in-service failure. Recovered gRPC and "
                "service-discovery evidence improves "
                "coverage and specificity rather than "
                "repairing the answer."
            ),
    },

    "dev-020": {
        "label":
            "retrieval_gap_not_answer_limiting",

        "material_answer_improvement":
            False,

        "reason":
            (
                "The Dense baseline already distinguishes "
                "network or resolution failure from "
                "application-level Payment failure using "
                "server-span presence, UNAVAILABLE and "
                "resolver diagnostics, and Payment logs. "
                "The recovered gRPC guide adds detail but "
                "does not change the core answer."
            ),
    },

    "dev-021": {
        "label":
            "retrieval_gap_not_answer_limiting",

        "material_answer_improvement":
            False,

        "reason":
            (
                "Despite low baseline qrel citation "
                "recall, the Dense answer already gives "
                "a complete investigation workflow from "
                "metrics through traces, logs, healthy "
                "comparison, hypothesis rejection, and "
                "final conclusion or abstention. The "
                "intervention improves documentary "
                "coverage but not task completion."
            ),
    },

    "dev-022": {
        "label":
            "retrieval_gap_not_answer_limiting",

        "material_answer_improvement":
            False,

        "reason":
            (
                "The Dense baseline already explains "
                "how to separate retry latency from a "
                "slow downstream dependency using traces, "
                "attempt counts, per-attempt latency, "
                "server spans, parent duration, and the "
                "critical path. The recovered metrics "
                "guide is supplementary."
            ),
    },

    "dev-023": {
        "label":
            "retrieval_gap_not_answer_limiting",

        "material_answer_improvement":
            False,

        "reason":
            (
                "The Dense baseline directly identifies "
                "payment-monitoring.md as the correct "
                "document for dashboard and alert design. "
                "The recovered metrics guide is not cited "
                "because it is unnecessary for answering "
                "the question."
            ),
    },
}


VALID_LABELS = {
    "retrieval_limited",
    "evidence_utilization_limited",
    "generation_reasoning_limited",
    "retrieval_gap_not_answer_limiting",
    "inconclusive",
}


def load_json(
    path: Path,
) -> dict:

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def main() -> None:

    comparison = load_json(
        INPUT_FILE
    )

    rows = comparison.get(
        "queries",
        []
    )

    comparison_ids = {
        row[
            "query_id"
        ]
        for row
        in rows
    }

    if (
        comparison_ids
        != set(
            ATTRIBUTIONS
        )
    ):
        raise RuntimeError(
            "Attribution IDs do not match "
            "the comparison artifact."
        )

    counts = Counter()

    final_rows = []

    for row in rows:

        query_id = (
            row[
                "query_id"
            ]
        )

        attribution = (
            ATTRIBUTIONS[
                query_id
            ]
        )

        label = (
            attribution[
                "label"
            ]
        )

        if label not in VALID_LABELS:

            raise RuntimeError(
                "Invalid attribution label: "
                f"{label}"
            )

        counts[
            label
        ] += 1

        final_row = dict(
            row
        )

        final_row[
            "human_attribution"
        ] = {
            "label":
                label,

            "material_answer_improvement":
                attribution[
                    "material_answer_improvement"
                ],

            "reason":
                attribution[
                    "reason"
                ],
        }

        final_rows.append(
            final_row
        )

    output = {
        "metadata": {
            "experiment":
                "014E",

            "version":
                "v1",

            "attribution_method":
                "human_pairwise_answer_inspection",

            "important_note":
                (
                    "Qrel relevance is not treated "
                    "as claim entailment or answer "
                    "correctness. Attribution is based "
                    "on whether the controlled evidence "
                    "intervention materially changes "
                    "answer sufficiency."
                ),
        },

        "summary": {
            label:
                counts[
                    label
                ]
            for label
            in sorted(
                VALID_LABELS
            )
        },

        "aggregate":
            comparison.get(
                "aggregate",
                {}
            ),

        "queries":
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

    print(
        "Experiment 014E — "
        "Final Failure Attribution"
    )

    print()

    for label in sorted(
        VALID_LABELS
    ):

        print(
            f"{label}: "
            f"{counts[label]}"
        )

    print()

    print(
        "Saved final attribution to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()