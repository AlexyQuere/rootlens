from rootlens.retrieval.tfidf_retriever import TfidfRetriever


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


def test_tfidf_retriever_returns_relevant_document_first():
    retriever = TfidfRetriever(DOCUMENTS)

    results = retriever.search(
        "Checkout PaymentService",
        k=3,
    )

    assert results[0][0] == "checkout.md"


def test_tfidf_retriever_respects_k():
    retriever = TfidfRetriever(DOCUMENTS)

    results = retriever.search(
        "service",
        k=1,
    )

    assert len(results) <= 1


def test_tfidf_retriever_returns_empty_for_unknown_query():
    retriever = TfidfRetriever(DOCUMENTS)

    results = retriever.search(
        "kubernetes postgres",
        k=3,
    )

    assert results == []