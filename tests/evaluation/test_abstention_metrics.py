import pytest

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


def test_perfect_predictions():

    gold = [
        "answered",
        "partial",
        "abstained",
    ]

    predicted = list(
        gold
    )

    assert accuracy(
        gold,
        predicted,
    ) == pytest.approx(
        1.0
    )

    assert macro_f1(
        gold,
        predicted,
    ) == pytest.approx(
        1.0
    )

    assert balanced_accuracy(
        gold,
        predicted,
    ) == pytest.approx(
        1.0
    )


def test_failure_to_abstain():

    gold = [
        "abstained",
        "abstained",
    ]

    predicted = [
        "answered",
        "abstained",
    ]

    assert (
        failure_to_abstain_rate(
            gold,
            predicted,
        )
        == pytest.approx(
            0.5
        )
    )


def test_partial_failure_modes():

    gold = [
        "partial",
        "partial",
    ]

    predicted = [
        "answered",
        "abstained",
    ]

    assert (
        partial_overclaim_rate(
            gold,
            predicted,
        )
        == pytest.approx(
            0.5
        )
    )

    assert (
        partial_overabstain_rate(
            gold,
            predicted,
        )
        == pytest.approx(
            0.5
        )
    )


def test_confusion_matrix():

    matrix = confusion_matrix(
        [
            "answered",
            "partial",
            "abstained",
        ],
        [
            "answered",
            "answered",
            "abstained",
        ],
    )

    assert (
        matrix[
            "answered"
        ][
            "answered"
        ]
        == 1
    )

    assert (
        matrix[
            "partial"
        ][
            "answered"
        ]
        == 1
    )


def test_triplet_consistency():

    rows = [
        {
            "pair_id": "a",
            "variant": "answerable",
            "correct": True,
        },
        {
            "pair_id": "a",
            "variant": "partial",
            "correct": True,
        },
        {
            "pair_id": "a",
            "variant": "unanswerable",
            "correct": True,
        },
        {
            "pair_id": "b",
            "variant": "answerable",
            "correct": True,
        },
        {
            "pair_id": "b",
            "variant": "partial",
            "correct": False,
        },
        {
            "pair_id": "b",
            "variant": "unanswerable",
            "correct": True,
        },
    ]

    assert (
        triplet_consistency_rate(
            rows
        )
        == pytest.approx(
            0.5
        )
    )