import math

import pytest

from rootlens.retrieval.reranker import (
    RerankedRetriever,
)


DOCUMENTS = {
    "a.md": "alpha evidence",
    "b.md": "beta evidence",
    "c.md": "gamma evidence",
}


class FakeCandidateRetriever:
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


class FakeReranker:
    def __init__(
        self,
        scores: list[float],
    ) -> None:
        self.scores = scores

    def score(
        self,
        query: str,
        documents,
    ) -> list[float]:
        return self.scores[:len(documents)]


def test_reranking_changes_order():
    retriever = RerankedRetriever(
        FakeCandidateRetriever(
            [
                ("a.md", 0.9),
                ("b.md", 0.8),
                ("c.md", 0.7),
            ]
        ),
        documents=DOCUMENTS,
        reranker=FakeReranker(
            [0.1, 0.9, 0.5]
        ),
        candidate_k=3,
    )

    results = retriever.search(
        "query",
        k=3,
    )

    assert [
        document_id
        for document_id, _
        in results
    ] == [
        "b.md",
        "c.md",
        "a.md",
    ]


def test_non_finite_scores_are_rejected():
    retriever = RerankedRetriever(
        FakeCandidateRetriever(
            [
                ("a.md", 0.9),
                ("b.md", 0.8),
            ]
        ),
        documents=DOCUMENTS,
        reranker=FakeReranker(
            [float("nan"), 0.5]
        ),
        candidate_k=2,
    )

    with pytest.raises(
        RuntimeError,
        match="non-finite",
    ):
        retriever.search(
            "query",
            k=2,
        )


def test_positive_infinity_is_rejected():
    retriever = RerankedRetriever(
        FakeCandidateRetriever(
            [
                ("a.md", 0.9),
                ("b.md", 0.8),
            ]
        ),
        documents=DOCUMENTS,
        reranker=FakeReranker(
            [float("inf"), 0.5]
        ),
        candidate_k=2,
    )

    with pytest.raises(
        RuntimeError,
        match="non-finite",
    ):
        retriever.search(
            "query",
            k=2,
        )
