import math

from rootlens.evaluation.retrieval_metrics import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_precision_at_k():
    retrieved = ["A", "B", "C"]
    relevant = {"A", "C"}

    result = precision_at_k(
        retrieved,
        relevant,
        k=3,
    )

    assert math.isclose(
        result,
        2 / 3,
    )


def test_recall_at_k():
    retrieved = ["A", "B", "C"]
    relevant = {"A", "C"}

    result = recall_at_k(
        retrieved,
        relevant,
        k=3,
    )

    assert result == 1.0


def test_reciprocal_rank_first_result():
    retrieved = ["A", "B", "C"]
    relevant = {"A"}

    assert reciprocal_rank(
        retrieved,
        relevant,
    ) == 1.0


def test_reciprocal_rank_third_result():
    retrieved = ["A", "B", "C"]
    relevant = {"C"}

    assert math.isclose(
        reciprocal_rank(
            retrieved,
            relevant,
        ),
        1 / 3,
    )


def test_reciprocal_rank_no_relevant_result():
    retrieved = ["A", "B"]
    relevant = {"C"}

    assert reciprocal_rank(
        retrieved,
        relevant,
    ) == 0.0