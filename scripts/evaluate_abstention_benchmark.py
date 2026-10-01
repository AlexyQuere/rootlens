from __future__ import annotations

import json
import math
import statistics

from collections import Counter
from pathlib import Path

from rootlens.evaluation.abstention_metrics import (
    accuracy,
    balanced_accuracy,
    class_metrics,
    confusion_matrix,
    failure_to_abstain_rate,
    macro_f1,
    partial_overabstain_rate,
    partial_overclaim_rate,
    triplet_consistency_rate,
)


ROOT = Path(__file__).resolve().parents[1]

EVALUATION_DIR = (
    ROOT
    / "data"
    / "evaluation"
)

OUTPUTS_FILE = (
    EVALUATION_DIR
    / "abstention_outputs_v1.json"
)

GOLD_FILE = (
    EVALUATION_DIR
    / "abstention_gold_v1.json"
)

RESULTS_FILE = (
    EVALUATION_DIR
    / "abstention_eval_v1.json"
)


STATUSES = (
    "answered",
    "partial",
    "abstained",
)


def load_json(
    path: Path,
):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def percentile(
    values: list[float],
    q: float,
) -> float:

    if not values:
        return 0.0

    if not (
        0.0
        <= q
        <= 1.0
    ):
        raise ValueError(
            "q must be between 0 and 1."
        )

    ordered = sorted(
        values
    )

    #
    # Nearest-rank percentile.
    #
    rank = max(
        1,
        math.ceil(
            q
            * len(
                ordered
            )
        ),
    )

    return ordered[
        rank - 1
    ]


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


def validate_frozen_item(
    item: dict,
) -> None:

    answer = item.get(
        "answer"
    )

    if not isinstance(
        answer,
        dict,
    ):
        raise ValueError(
            "answer must be an object."
        )

    status = answer.get(
        "status"
    )

    claims = answer.get(
        "claims"
    )

    limitation = answer.get(
        "limitation"
    )

    if status not in STATUSES:
        raise ValueError(
            "Invalid status: "
            f"{status!r}"
        )

    if not isinstance(
        claims,
        list,
    ):
        raise ValueError(
            "claims must be a list."
        )

    if status == "answered":

        if not claims:
            raise ValueError(
                "answered output must "
                "contain claims."
            )

        if limitation is not None:
            raise ValueError(
                "answered output must "
                "not contain limitation."
            )

    elif status == "partial":

        if not claims:
            raise ValueError(
                "partial output must "
                "contain claims."
            )

        if (
            not isinstance(
                limitation,
                str,
            )
            or not limitation.strip()
        ):
            raise ValueError(
                "partial output must "
                "contain a limitation."
            )

    elif status == "abstained":

        if claims:
            raise ValueError(
                "abstained output must "
                "not contain claims."
            )

        if (
            not isinstance(
                limitation,
                str,
            )
            or not limitation.strip()
        ):
            raise ValueError(
                "abstained output must "
                "contain a limitation."
            )


def main() -> None:

    outputs = load_json(
        OUTPUTS_FILE
    )

    gold_data = load_json(
        GOLD_FILE
    )

    metadata = outputs.get(
        "metadata",
        {}
    )

    if (
        metadata.get(
            "gold_loaded_during_generation"
        )
        is not False
    ):
        raise RuntimeError(
            "Generation artifact does not "
            "confirm that gold labels were "
            "hidden."
        )

    output_items = outputs.get(
        "items",
        []
    )

    gold_items = gold_data.get(
        "gold",
        []
    )

    if len(
        output_items
    ) != 18:

        raise RuntimeError(
            "Expected 18 frozen outputs, "
            f"got {len(output_items)}."
        )

    if len(
        gold_items
    ) != 18:

        raise RuntimeError(
            "Expected 18 gold items, "
            f"got {len(gold_items)}."
        )

    output_by_id = {
        item[
            "query_id"
        ]:
            item
        for item
        in output_items
    }

    gold_by_id = {
        item[
            "query_id"
        ]:
            item
        for item
        in gold_items
    }

    if (
        set(
            output_by_id
        )
        != set(
            gold_by_id
        )
    ):
        raise RuntimeError(
            "Output IDs and gold IDs "
            "do not match."
        )

    gold_statuses = []

    predicted_statuses = []

    rows = []

    latencies = []

    generation_attempts = []

    expected_source_hits = []

    predicted_counts = Counter()

    print(
        "Experiment 014D — "
        "Abstention Evaluation"
    )

    print(
        f"Queries: "
        f"{len(output_items)}"
    )

    print(
        "Gold hidden during generation: "
        "True"
    )

    print()

    #
    # Preserve generation order.
    #
    for item in output_items:

        validate_frozen_item(
            item
        )

        query_id = (
            item[
                "query_id"
            ]
        )

        gold = (
            gold_by_id[
                query_id
            ]
        )

        expected = (
            gold[
                "expected_status"
            ]
        )

        predicted = (
            item[
                "answer"
            ][
                "status"
            ]
        )

        correct = (
            expected
            == predicted
        )

        gold_statuses.append(
            expected
        )

        predicted_statuses.append(
            predicted
        )

        predicted_counts[
            predicted
        ] += 1

        latency = float(
            item.get(
                "latency_ms",
                0.0,
            )
        )

        attempts = int(
            item.get(
                "generation_attempts",
                1,
            )
        )

        latencies.append(
            latency
        )

        generation_attempts.append(
            attempts
        )

        cited = cited_sources(
            item
        )

        expected_sources = set(
            gold.get(
                "expected_sources",
                []
            )
        )

        if expected_sources:

            expected_source_hit = bool(
                cited
                & expected_sources
            )

            expected_source_hits.append(
                expected_source_hit
            )

        else:

            expected_source_hit = None

        row = {
            "query_id":
                query_id,

            "pair_id":
                item[
                    "pair_id"
                ],

            "variant":
                item[
                    "variant"
                ],

            "expected_status":
                expected,

            "predicted_status":
                predicted,

            "correct":
                correct,

            "expected_sources":
                sorted(
                    expected_sources
                ),

            "cited_sources":
                sorted(
                    cited
                ),

            "expected_source_hit":
                expected_source_hit,

            "supported_component":
                gold.get(
                    "supported_component"
                ),

            "missing_component":
                gold.get(
                    "missing_component"
                ),

            "limitation":
                item[
                    "answer"
                ][
                    "limitation"
                ],

            "generation_attempts":
                attempts,

            "latency_ms":
                latency,
        }

        rows.append(
            row
        )

    matrix = confusion_matrix(
        gold_statuses,
        predicted_statuses,
    )

    overall_accuracy = accuracy(
        gold_statuses,
        predicted_statuses,
    )

    overall_macro_f1 = macro_f1(
        gold_statuses,
        predicted_statuses,
    )

    overall_balanced_accuracy = (
        balanced_accuracy(
            gold_statuses,
            predicted_statuses,
        )
    )

    per_class = {
        label:
            class_metrics(
                gold_statuses,
                predicted_statuses,
                label,
            )
        for label in STATUSES
    }

    fail_to_abstain = (
        failure_to_abstain_rate(
            gold_statuses,
            predicted_statuses,
        )
    )

    partial_overclaim = (
        partial_overclaim_rate(
            gold_statuses,
            predicted_statuses,
        )
    )

    partial_overabstain = (
        partial_overabstain_rate(
            gold_statuses,
            predicted_statuses,
        )
    )

    triplet_rate = (
        triplet_consistency_rate(
            rows
        )
    )

    retry_count = sum(
        attempts > 1
        for attempts
        in generation_attempts
    )

    retry_rate = (
        retry_count
        / len(
            generation_attempts
        )
    )

    mean_attempts = (
        statistics.mean(
            generation_attempts
        )
    )

    mean_latency = (
        statistics.mean(
            latencies
        )
    )

    median_latency = (
        statistics.median(
            latencies
        )
    )

    p95_latency = percentile(
        latencies,
        0.95,
    )

    source_hit_rate = (
        sum(
            expected_source_hits
        )
        / len(
            expected_source_hits
        )
        if expected_source_hits
        else None
    )

    print(
        "=== Status Distribution ==="
    )

    for status in STATUSES:

        print(
            f"{status:<10} "
            f"{predicted_counts[status]}"
        )

    print()

    print(
        "=== Confusion Matrix ==="
    )

    print(
        "Gold \\ Predicted"
    )

    print(
        "               "
        "answered  partial  abstained"
    )

    for expected in STATUSES:

        values = [
            matrix[
                expected
            ][
                predicted
            ]
            for predicted
            in STATUSES
        ]

        print(
            f"{expected:<13}"
            f"{values[0]:>8}"
            f"{values[1]:>9}"
            f"{values[2]:>11}"
        )

    print()

    print(
        "=== Classification ==="
    )

    print(
        "Accuracy: "
        f"{overall_accuracy:.4f}"
    )

    print(
        "Balanced accuracy: "
        f"{overall_balanced_accuracy:.4f}"
    )

    print(
        "Macro-F1: "
        f"{overall_macro_f1:.4f}"
    )

    print()

    print(
        "Per class:"
    )

    for label in STATUSES:

        metrics = (
            per_class[
                label
            ]
        )

        print(
            f"  {label}"
        )

        print(
            "    precision="
            f"{metrics['precision']:.4f}"
        )

        print(
            "    recall="
            f"{metrics['recall']:.4f}"
        )

        print(
            "    f1="
            f"{metrics['f1']:.4f}"
        )

    print()

    print(
        "=== Safety / Selectivity ==="
    )

    print(
        "Failure-to-abstain rate: "
        f"{fail_to_abstain:.4f}"
    )

    print(
        "Partial overclaim rate: "
        f"{partial_overclaim:.4f}"
    )

    print(
        "Partial over-abstain rate: "
        f"{partial_overabstain:.4f}"
    )

    print()

    print(
        "=== Matched Triplets ==="
    )

    print(
        "Triplet consistency rate: "
        f"{triplet_rate:.4f}"
    )

    pair_ids = []

    for row in rows:

        pair_id = (
            row[
                "pair_id"
            ]
        )

        if pair_id not in pair_ids:
            pair_ids.append(
                pair_id
            )

    for pair_id in pair_ids:

        pair_rows = [
            row
            for row in rows
            if (
                row[
                    "pair_id"
                ]
                == pair_id
            )
        ]

        order = {
            "answerable": 0,
            "partial": 1,
            "unanswerable": 2,
        }

        pair_rows.sort(
            key=lambda row:
                order[
                    row[
                        "variant"
                    ]
                ]
        )

        transition = (
            " -> ".join(
                row[
                    "predicted_status"
                ]
                for row
                in pair_rows
            )
        )

        pair_correct = all(
            row[
                "correct"
            ]
            for row
            in pair_rows
        )

        print(
            f"  {pair_id}: "
            f"{transition} "
            f"| correct={pair_correct}"
        )

    print()

    print(
        "=== Evidence Sanity Check ==="
    )

    if source_hit_rate is None:

        print(
            "Expected-source hit rate: N/A"
        )

    else:

        print(
            "Expected-source hit rate "
            "for answerable/partial cases: "
            f"{source_hit_rate:.4f}"
        )

    print(
        "NOTE: this is not a "
        "groundedness metric."
    )

    print()

    print(
        "=== Generation Reliability ==="
    )

    print(
        "Schema retries: "
        f"{retry_count}/"
        f"{len(generation_attempts)} "
        f"({retry_rate:.4f})"
    )

    print(
        "Mean generation attempts: "
        f"{mean_attempts:.3f}"
    )

    print(
        "Mean latency_ms: "
        f"{mean_latency:.1f}"
    )

    print(
        "Median latency_ms: "
        f"{median_latency:.1f}"
    )

    print(
        "P95 latency_ms: "
        f"{p95_latency:.1f}"
    )

    print()

    print(
        "=== Errors ==="
    )

    errors = [
        row
        for row in rows
        if not row[
            "correct"
        ]
    ]

    if not errors:

        print(
            "No status classification errors."
        )

    else:

        for row in errors:

            print(
                f"{row['query_id']}: "
                f"expected="
                f"{row['expected_status']} "
                f"predicted="
                f"{row['predicted_status']}"
            )

    results = {
        "metadata": {
            "experiment":
                "014D",

            "version":
                "v1",

            "outputs_file":
                OUTPUTS_FILE.name,

            "gold_file":
                GOLD_FILE.name,

            "gold_hidden_during_generation":
                True,

            "important_note":
                (
                    "This is a small synthetic "
                    "matched-triplet calibration "
                    "benchmark, not a broad "
                    "population estimate."
                ),
        },

        "classification": {
            "accuracy":
                overall_accuracy,

            "balanced_accuracy":
                overall_balanced_accuracy,

            "macro_f1":
                overall_macro_f1,

            "confusion_matrix":
                matrix,

            "per_class":
                per_class,
        },

        "selectivity": {
            "failure_to_abstain_rate":
                fail_to_abstain,

            "partial_overclaim_rate":
                partial_overclaim,

            "partial_overabstain_rate":
                partial_overabstain,

            "triplet_consistency_rate":
                triplet_rate,
        },

        "evidence": {
            "expected_source_hit_rate":
                source_hit_rate,

            "note":
                (
                    "Expected-source overlap "
                    "is not claim-level "
                    "groundedness."
                ),
        },

        "generation": {
            "schema_retry_count":
                retry_count,

            "schema_retry_rate":
                retry_rate,

            "mean_attempts":
                mean_attempts,

            "mean_latency_ms":
                mean_latency,

            "median_latency_ms":
                median_latency,

            "p95_latency_ms":
                p95_latency,
        },

        "queries":
            rows,
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