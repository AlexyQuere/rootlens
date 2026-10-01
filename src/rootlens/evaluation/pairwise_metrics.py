from __future__ import annotations

from collections import Counter
from typing import Sequence


VALID_PREFERENCES = (
    "dense",
    "semantic",
    "tie",
)


def _validate(
    values: Sequence[str],
) -> None:

    invalid = [
        value
        for value in values
        if value not in VALID_PREFERENCES
    ]

    if invalid:
        raise ValueError(
            "Invalid pairwise preferences: "
            f"{invalid}"
        )


def preference_counts(
    values: Sequence[str],
) -> dict[str, int]:

    _validate(
        values
    )

    counts = Counter(
        values
    )

    return {
        label:
            counts[label]
        for label
        in VALID_PREFERENCES
    }


def exact_agreement(
    left: Sequence[str],
    right: Sequence[str],
) -> float:

    if len(left) != len(right):
        raise ValueError(
            "Sequences must have "
            "the same length."
        )

    if not left:
        return 0.0

    _validate(left)
    _validate(right)

    agreements = sum(
        a == b
        for a, b
        in zip(
            left,
            right,
        )
    )

    return (
        agreements
        / len(left)
    )


def confusion_matrix(
    left: Sequence[str],
    right: Sequence[str],
) -> dict[
    str,
    dict[str, int],
]:

    if len(left) != len(right):
        raise ValueError(
            "Sequences must have "
            "the same length."
        )

    _validate(left)
    _validate(right)

    matrix = {
        row: {
            column: 0
            for column
            in VALID_PREFERENCES
        }
        for row
        in VALID_PREFERENCES
    }

    for a, b in zip(
        left,
        right,
    ):

        matrix[a][b] += 1

    return matrix


def cohen_kappa(
    left: Sequence[str],
    right: Sequence[str],
) -> float | None:

    if len(left) != len(right):
        raise ValueError(
            "Sequences must have "
            "the same length."
        )

    if not left:
        return None

    _validate(left)
    _validate(right)

    n = len(left)

    observed = (
        exact_agreement(
            left,
            right,
        )
    )

    left_counts = (
        preference_counts(
            left
        )
    )

    right_counts = (
        preference_counts(
            right
        )
    )

    expected = sum(
        (
            left_counts[label]
            / n
        )
        * (
            right_counts[label]
            / n
        )
        for label
        in VALID_PREFERENCES
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


def non_tie_rate(
    values: Sequence[str],
) -> float:

    if not values:
        return 0.0

    _validate(values)

    return (
        sum(
            value != "tie"
            for value
            in values
        )
        / len(values)
    )


def consensus_label(
    left: str,
    right: str,
) -> str:

    _validate(
        [left, right]
    )

    if left == right:
        return left

    return "disagreement"