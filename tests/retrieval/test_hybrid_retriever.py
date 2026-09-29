import math

from rootlens.retrieval.hybrid_retriever import (
    HybridRetriever,
)


class FakeRetriever:
    def __init__(
        self,
        results: list[tuple[str, float]],
    ) -> None:
        self.results = results

    def search(
        self,
        query: str,
        k: int = 5,
    ) -> list[tuple[str, float]]:
        return self.results[:k]


def test_rrf_rewards_documents_present_in_both_rankings():
    lexical = FakeRetriever(
        [
            ("A", 10.0),
            ("B", 8.0),
            ("C", 5.0),
        ]
    )

    dense = FakeRetriever(
        [
            ("C", 0.9),
            ("A", 0.8),
            ("D", 0.7),
        ]
    )

    retriever = HybridRetriever(
        lexical,
        dense,
        rrf_k=60,
    )

    results = retriever.search(
        "query",
        k=4,
    )

    ranked_ids = [
        document_id
        for document_id, _
        in results
    ]

    assert ranked_ids[0] in {
        "A",
        "C",
    }

    assert ranked_ids.index("A") < ranked_ids.index("B")
    assert ranked_ids.index("C") < ranked_ids.index("D")

def test_rrf_score():
    lexical = FakeRetriever(
        [
            ("A", 1.0),
        ]
    )

    dense = FakeRetriever(
        [
            ("A", 1.0),
        ]
    )

    retriever = HybridRetriever(
        lexical,
        dense,
        rrf_k=60,
    )

    results = retriever.search(
        "query",
        k=1,
    )

    _, score = results[0]

    expected = (
        1 / 61
        + 1 / 61
    )

    assert math.isclose(
        score,
        expected,
    )

def test_rrf_can_promote_lower_ranked_candidates():
    lexical = FakeRetriever(
        [
            ("A", 1.0),
            ("X", 0.8),
            ("C", 0.7),
        ]
    )

    dense = FakeRetriever(
        [
            ("B", 1.0),
            ("X", 0.8),
            ("D", 0.7),
        ]
    )

    retriever = HybridRetriever(
        lexical,
        dense,
    )

    results = retriever.search(
        "query",
        k=2,
        candidate_k=3,
    )

    ranked_ids = [
        document_id
        for document_id, _
        in results
    ]

    assert "X" in ranked_ids