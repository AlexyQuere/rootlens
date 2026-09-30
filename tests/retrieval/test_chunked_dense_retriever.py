import numpy as np
import pytest

from rootlens.retrieval.chunked_dense_retriever import (
    ChunkedDenseRetriever,
)


class FakeEncoder:
    """Deterministic encoder used to test retrieval logic.

    The purpose is not to test embedding quality.
    We only want to verify:

    - chunk scoring;
    - chunk -> document aggregation;
    - ranking;
    - top-k behaviour.
    """

    def encode_documents(
        self,
        documents: list[str],
    ) -> np.ndarray:
        vectors = []

        for text in documents:
            if "resolution failure" in text:
                vector = np.array(
                    [1.0, 0.0]
                )

            elif "payment" in text:
                vector = np.array(
                    [0.6, 0.8]
                )

            elif "shipping" in text:
                vector = np.array(
                    [0.0, 1.0]
                )

            else:
                vector = np.array(
                    [0.0, 0.0]
                )

            vectors.append(vector)

        return np.array(vectors)

    def encode_query(
        self,
        query: str,
    ) -> np.ndarray:
        if query == "resolution problem":
            return np.array(
                [1.0, 0.0]
            )

        if query == "shipping problem":
            return np.array(
                [0.0, 1.0]
            )

        return np.array(
            [0.0, 0.0]
        )


DOCUMENTS = {
    "service-discovery.md": (
        "generic introduction text "
        "resolution failure detected"
    ),
    "payment.md": (
        "payment processing information "
        "payment monitoring information"
    ),
    "shipping.md": (
        "shipping delivery information"
    ),
}


def test_chunked_retriever_ranks_document_using_best_chunk():
    retriever = ChunkedDenseRetriever(
        DOCUMENTS,
        encoder=FakeEncoder(),
        chunk_size_words=3,
        overlap_words=0,
    )

    results = retriever.search(
        "resolution problem",
        k=3,
    )

    assert results[0][0] == (
        "service-discovery.md"
    )


def test_chunked_retriever_returns_unique_documents():
    retriever = ChunkedDenseRetriever(
        DOCUMENTS,
        encoder=FakeEncoder(),
        chunk_size_words=3,
        overlap_words=0,
    )

    results = retriever.search(
        "resolution problem",
        k=3,
    )

    document_ids = [
        document_id
        for document_id, _
        in results
    ]

    assert len(document_ids) == len(
        set(document_ids)
    )


def test_chunked_retriever_respects_k():
    retriever = ChunkedDenseRetriever(
        DOCUMENTS,
        encoder=FakeEncoder(),
        chunk_size_words=3,
        overlap_words=0,
    )

    results = retriever.search(
        "resolution problem",
        k=1,
    )

    assert len(results) == 1


def test_search_chunks_returns_individual_chunks():
    retriever = ChunkedDenseRetriever(
        DOCUMENTS,
        encoder=FakeEncoder(),
        chunk_size_words=3,
        overlap_words=0,
    )

    results = retriever.search_chunks(
        "resolution problem",
        k=3,
    )

    best_chunk, best_score = results[0]

    assert best_chunk.document_id == (
        "service-discovery.md"
    )

    assert (
        "resolution failure"
        in best_chunk.text
    )

    assert best_score == 1.0


def test_document_score_is_maximum_chunk_score():
    retriever = ChunkedDenseRetriever(
        DOCUMENTS,
        encoder=FakeEncoder(),
        chunk_size_words=3,
        overlap_words=0,
    )

    results = dict(
        retriever.search(
            "resolution problem",
            k=3,
        )
    )

    # One chunk of service-discovery.md
    # receives [1, 0], while the other
    # chunk is unrelated.
    #
    # The document-level score must
    # therefore be the maximum chunk score.
    assert results[
        "service-discovery.md"
    ] == 1.0


def test_invalid_k_is_rejected():
    retriever = ChunkedDenseRetriever(
        DOCUMENTS,
        encoder=FakeEncoder(),
        chunk_size_words=3,
        overlap_words=0,
    )

    with pytest.raises(ValueError):
        retriever.search(
            "resolution problem",
            k=0,
        )


def test_invalid_chunk_search_k_is_rejected():
    retriever = ChunkedDenseRetriever(
        DOCUMENTS,
        encoder=FakeEncoder(),
        chunk_size_words=3,
        overlap_words=0,
    )

    with pytest.raises(ValueError):
        retriever.search_chunks(
            "resolution problem",
            k=0,
        )