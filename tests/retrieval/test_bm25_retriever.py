from rootlens.retrieval.bm25_retriever import (
    BM25Retriever,
)
import pytest

DOCUMENTS = {
    "checkout.md": (
        "Checkout calls PaymentService during order processing."
    ),
    "shipping.md": (
        "Shipping calculates delivery quotes."
    ),
    "grpc.md": (
        "gRPC UNAVAILABLE can indicate a connectivity failure."
    ),
}


def test_bm25_returns_relevant_document_first():
    retriever = BM25Retriever(DOCUMENTS)

    results = retriever.search(
        "Checkout PaymentService",
        k=3,
    )

    assert results[0][0] == "checkout.md"


def test_bm25_returns_empty_for_unknown_query():
    retriever = BM25Retriever(DOCUMENTS)

    results = retriever.search(
        "kubernetes postgres",
        k=3,
    )

    assert results == []


def test_bm25_respects_k():
    retriever = BM25Retriever(DOCUMENTS)

    results = retriever.search(
        "checkout payment",
        k=1,
    )

    assert len(results) <= 1

def test_bm25_term_frequency_saturates():
    documents = {
        "once.md": "payment",
        "many.md": (
            "payment payment payment payment payment"
        ),
    }

    retriever = BM25Retriever(documents)

    results = dict(
        retriever.search(
            "payment",
            k=2,
        )
    )

    assert results["many.md"] > results["once.md"]

    assert (
        results["many.md"]
        < 5 * results["once.md"]
    )

def test_bm25_penalizes_longer_document():
    documents = {
        "short.md": "payment",
        "long.md": (
            "payment filler filler filler filler "
            "filler filler filler filler filler"
        ),
    }

    retriever = BM25Retriever(documents)

    results = dict(
        retriever.search(
            "payment",
            k=2,
        )
    )

    assert (
        results["short.md"]
        > results["long.md"]
    )

def test_bm25_rejects_invalid_k1():
    with pytest.raises(ValueError):
        BM25Retriever(
            DOCUMENTS,
            k1=0.0,
        )


def test_bm25_rejects_invalid_b():
    with pytest.raises(ValueError):
        BM25Retriever(
            DOCUMENTS,
            b=1.5,
        )