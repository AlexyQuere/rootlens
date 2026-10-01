from __future__ import annotations

from collections import Counter


STATUSES = (
    "answered",
    "partial",
    "abstained",
)


def confusion_matrix(
    gold: list[str],
    predicted: list[str],
) -> dict[str, dict[str, int]]:

    if len(gold) != len(predicted):
        raise ValueError(
            "gold and predicted must "
            "have the same length."
        )

    matrix = {
        expected: {
            actual: 0
            for actual in STATUSES
        }
        for expected in STATUSES
    }

    for expected, actual in zip(
        gold,
        predicted,
    ):

        if expected not in STATUSES:
            raise ValueError(
                f"Invalid gold status: "
                f"{expected}"
            )

        if actual not in STATUSES:
            raise ValueError(
                f"Invalid predicted status: "
                f"{actual}"
            )

        matrix[
            expected
        ][
            actual
        ] += 1

    return matrix


def accuracy(
    gold: list[str],
    predicted: list[str],
) -> float:

    if not gold:
        return 0.0

    return (
        sum(
            expected == actual
            for expected, actual
            in zip(
                gold,
                predicted,
            )
        )
        / len(gold)
    )


def class_metrics(
    gold: list[str],
    predicted: list[str],
    label: str,
) -> dict[str, float]:

    if label not in STATUSES:
        raise ValueError(
            f"Invalid label: {label}"
        )

    tp = sum(
        expected == label
        and actual == label
        for expected, actual
        in zip(
            gold,
            predicted,
        )
    )

    fp = sum(
        expected != label
        and actual == label
        for expected, actual
        in zip(
            gold,
            predicted,
        )
    )

    fn = sum(
        expected == label
        and actual != label
        for expected, actual
        in zip(
            gold,
            predicted,
        )
    )

    precision = (
        tp / (tp + fp)
        if (
            tp + fp
        )
        else 0.0
    )

    recall = (
        tp / (tp + fn)
        if (
            tp + fn
        )
        else 0.0
    )

    f1 = (
        2
        * precision
        * recall
        / (
            precision
            + recall
        )
        if (
            precision
            + recall
        )
        else 0.0
    )

    return {
        "precision":
            precision,

        "recall":
            recall,

        "f1":
            f1,
    }


def macro_f1(
    gold: list[str],
    predicted: list[str],
) -> float:

    return (
        sum(
            class_metrics(
                gold,
                predicted,
                label,
            )[
                "f1"
            ]
            for label in STATUSES
        )
        / len(STATUSES)
    )


def balanced_accuracy(
    gold: list[str],
    predicted: list[str],
) -> float:

    return (
        sum(
            class_metrics(
                gold,
                predicted,
                label,
            )[
                "recall"
            ]
            for label in STATUSES
        )
        / len(STATUSES)
    )


def failure_to_abstain_rate(
    gold: list[str],
    predicted: list[str],
) -> float:

    indices = [
        index
        for index, status
        in enumerate(gold)
        if status == "abstained"
    ]

    if not indices:
        return 0.0

    failures = sum(
        predicted[
            index
        ]
        != "abstained"
        for index in indices
    )

    return (
        failures
        / len(indices)
    )


def partial_overclaim_rate(
    gold: list[str],
    predicted: list[str],
) -> float:

    indices = [
        index
        for index, status
        in enumerate(gold)
        if status == "partial"
    ]

    if not indices:
        return 0.0

    failures = sum(
        predicted[
            index
        ]
        == "answered"
        for index in indices
    )

    return (
        failures
        / len(indices)
    )


def partial_overabstain_rate(
    gold: list[str],
    predicted: list[str],
) -> float:

    indices = [
        index
        for index, status
        in enumerate(gold)
        if status == "partial"
    ]

    if not indices:
        return 0.0

    failures = sum(
        predicted[
            index
        ]
        == "abstained"
        for index in indices
    )

    return (
        failures
        / len(indices)
    )


def triplet_consistency_rate(
    rows: list[dict],
) -> float:

    pairs = {}

    for row in rows:

        pair_id = (
            row[
                "pair_id"
            ]
        )

        variant = (
            row[
                "variant"
            ]
        )

        pairs.setdefault(
            pair_id,
            {}
        )[
            variant
        ] = (
            row[
                "correct"
            ]
        )

    if not pairs:
        return 0.0

    expected_variants = {
        "answerable",
        "partial",
        "unanswerable",
    }

    correct_pairs = 0

    for pair_id, variants in (
        pairs.items()
    ):

        if (
            set(variants)
            != expected_variants
        ):

            raise ValueError(
                "Incomplete triplet for "
                f"{pair_id}"
            )

        if all(
            variants.values()
        ):
            correct_pairs += 1

    return (
        correct_pairs
        / len(pairs)
    )