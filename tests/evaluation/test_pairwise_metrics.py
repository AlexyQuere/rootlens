import pytest

from rootlens.evaluation.pairwise_metrics import (
    cohen_kappa,
    confusion_matrix,
    consensus_label,
    exact_agreement,
    non_tie_rate,
    preference_counts,
)


def test_preference_counts():

    result = preference_counts(
        [
            "dense",
            "semantic",
            "tie",
            "tie",
        ]
    )

    assert result == {
        "dense": 1,
        "semantic": 1,
        "tie": 2,
    }


def test_exact_agreement():

    result = exact_agreement(
        [
            "dense",
            "semantic",
            "tie",
        ],
        [
            "dense",
            "tie",
            "tie",
        ],
    )

    assert result == pytest.approx(
        2 / 3
    )


def test_confusion_matrix():

    matrix = confusion_matrix(
        [
            "dense",
            "semantic",
            "tie",
        ],
        [
            "dense",
            "tie",
            "semantic",
        ],
    )

    assert (
        matrix[
            "dense"
        ][
            "dense"
        ]
        == 1
    )

    assert (
        matrix[
            "semantic"
        ][
            "tie"
        ]
        == 1
    )

    assert (
        matrix[
            "tie"
        ][
            "semantic"
        ]
        == 1
    )


def test_non_tie_rate():

    result = non_tie_rate(
        [
            "dense",
            "tie",
            "semantic",
            "tie",
        ]
    )

    assert result == pytest.approx(
        0.5
    )


def test_consensus_label():

    assert (
        consensus_label(
            "dense",
            "dense",
        )
        == "dense"
    )

    assert (
        consensus_label(
            "semantic",
            "semantic",
        )
        == "semantic"
    )

    assert (
        consensus_label(
            "tie",
            "tie",
        )
        == "tie"
    )

    assert (
        consensus_label(
            "dense",
            "semantic",
        )
        == "disagreement"
    )


def test_perfect_kappa():

    labels = [
        "dense",
        "semantic",
        "tie",
        "dense",
    ]

    result = cohen_kappa(
        labels,
        labels,
    )

    assert result == pytest.approx(
        1.0
    )