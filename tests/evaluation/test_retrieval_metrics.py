import math

from rootlens.evaluation.retrieval_metrics import (
    dcg_at_k,
    ndcg_at_k,
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

def test_ndcg_is_one_for_ideal_ranking():
    relevance = {
        "A": 2,
        "B": 1,
    }

    retrieved = [
        "A",
        "B",
    ]

    result = ndcg_at_k(
        retrieved,
        relevance,
        k=2,
    )

    assert math.isclose(
        result,
        1.0,
    )


def test_ndcg_penalizes_wrong_order():
    relevance = {
        "A": 2,
        "B": 1,
    }

    ideal = ndcg_at_k(
        ["A", "B"],
        relevance,
        k=2,
    )

    reversed_ranking = ndcg_at_k(
        ["B", "A"],
        relevance,
        k=2,
    )

    assert reversed_ranking < ideal


def test_ndcg_penalizes_irrelevant_document():
    relevance = {
        "A": 2,
        "B": 1,
    }

    result = ndcg_at_k(
        ["A", "C"],
        relevance,
        k=2,
    )

    assert result < 1.0


def test_ndcg_returns_zero_without_relevant_documents():
    result = ndcg_at_k(
        ["A", "B"],
        {},
        k=2,
    )

    assert result == 0.0