import pytest

from rootlens.retrieval.reranker import (
    RerankedRetriever,
)


DOCUMENTS = {
    "a.md": "alpha evidence",
    "b.md": "beta evidence",
    "c.md": "gamma evidence",
    "d.md": "delta evidence",
}


class FakeCandidateRetriever:
    def __init__(
        self,
        results: list[tuple[str, float]],
    ) -> None:
        self.results = results
        self.last_k = None

    def search(
        self,
        query: str,
        k: int = 5,
    ) -> list[tuple[str, float]]:
        self.last_k = k
        return self.results[:k]


class FakeReranker:
    def __init__(
        self,
        scores_by_text: dict[str, float],
    ) -> None:
        self.scores_by_text = scores_by_text

    def score(
        self,
        query: str,
        documents,
    ) -> list[float]:
        return [
            self.scores_by_text[text]
            for text in documents
        ]


def test_reranker_changes_candidate_order():
    candidate_retriever = (
        FakeCandidateRetriever(
            [
                ("a.md", 0.95),
                ("b.md", 0.90),
                ("c.md", 0.85),
            ]
        )
    )

    reranker = FakeReranker(
        {
            "alpha evidence": 0.1,
            "beta evidence": 0.9,
            "gamma evidence": 0.5,
        }
    )

    retriever = RerankedRetriever(
        candidate_retriever,
        documents=DOCUMENTS,
        reranker=reranker,
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


def test_reranker_cannot_introduce_new_candidates():
    candidate_retriever = (
        FakeCandidateRetriever(
            [
                ("a.md", 0.95),
                ("b.md", 0.90),
            ]
        )
    )

    reranker = FakeReranker(
        {
            "alpha evidence": 0.1,
            "beta evidence": 0.9,
            "gamma evidence": 100.0,
        }
    )

    retriever = RerankedRetriever(
        candidate_retriever,
        documents=DOCUMENTS,
        reranker=reranker,
        candidate_k=2,
    )

    results = retriever.search(
        "query",
        k=5,
    )

    returned_ids = {
        document_id
        for document_id, _
        in results
    }

    assert returned_ids == {
        "a.md",
        "b.md",
    }

    assert "c.md" not in returned_ids


def test_candidate_k_is_passed_to_first_stage():
    candidate_retriever = (
        FakeCandidateRetriever(
            [
                ("a.md", 0.9),
                ("b.md", 0.8),
                ("c.md", 0.7),
                ("d.md", 0.6),
            ]
        )
    )

    reranker = FakeReranker(
        {
            text: 1.0
            for text in DOCUMENTS.values()
        }
    )

    retriever = RerankedRetriever(
        candidate_retriever,
        documents=DOCUMENTS,
        reranker=reranker,
        candidate_k=3,
    )

    retriever.search(
        "query",
        k=2,
    )

    assert (
        candidate_retriever.last_k
        == 3
    )


def test_reranked_retriever_respects_final_k():
    candidate_retriever = (
        FakeCandidateRetriever(
            [
                ("a.md", 0.9),
                ("b.md", 0.8),
                ("c.md", 0.7),
            ]
        )
    )

    reranker = FakeReranker(
        {
            "alpha evidence": 0.1,
            "beta evidence": 0.9,
            "gamma evidence": 0.5,
        }
    )

    retriever = RerankedRetriever(
        candidate_retriever,
        documents=DOCUMENTS,
        reranker=reranker,
        candidate_k=3,
    )

    results = retriever.search(
        "query",
        k=2,
    )

    assert len(results) == 2


def test_ties_are_broken_by_document_id():
    candidate_retriever = (
        FakeCandidateRetriever(
            [
                ("b.md", 0.9),
                ("a.md", 0.8),
            ]
        )
    )

    reranker = FakeReranker(
        {
            "alpha evidence": 0.5,
            "beta evidence": 0.5,
        }
    )

    retriever = RerankedRetriever(
        candidate_retriever,
        documents=DOCUMENTS,
        reranker=reranker,
        candidate_k=2,
    )

    results = retriever.search(
        "query",
        k=2,
    )

    assert [
        document_id
        for document_id, _
        in results
    ] == [
        "a.md",
        "b.md",
    ]


def test_invalid_candidate_k_is_rejected():
    with pytest.raises(ValueError):
        RerankedRetriever(
            FakeCandidateRetriever([]),
            documents=DOCUMENTS,
            reranker=FakeReranker({}),
            candidate_k=0,
        )


def test_invalid_final_k_is_rejected():
    retriever = RerankedRetriever(
        FakeCandidateRetriever([]),
        documents=DOCUMENTS,
        reranker=FakeReranker({}),
        candidate_k=3,
    )

    with pytest.raises(ValueError):
        retriever.search(
            "query",
            k=0,
        )


class BrokenReranker:
    def score(
        self,
        query: str,
        documents,
    ) -> list[float]:
        return [1.0]


def test_mismatched_reranker_scores_are_rejected():
    candidate_retriever = (
        FakeCandidateRetriever(
            [
                ("a.md", 0.9),
                ("b.md", 0.8),
            ]
        )
    )

    retriever = RerankedRetriever(
        candidate_retriever,
        documents=DOCUMENTS,
        reranker=BrokenReranker(),
        candidate_k=2,
    )

    with pytest.raises(ValueError):
        retriever.search(
            "query",
            k=2,
        )
