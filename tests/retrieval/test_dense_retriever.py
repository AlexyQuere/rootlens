import numpy as np

from rootlens.retrieval.dense_retriever import (
    DenseRetriever,
)


class FakeEncoder:
    def encode_documents(
        self,
        documents: list[str],
    ):
        vectors = {
            "payment document": np.array(
                [1.0, 0.0]
            ),
            "shipping document": np.array(
                [0.0, 1.0]
            ),
        }

        return np.array([
            vectors[document]
            for document in documents
        ])

    def encode_query(
        self,
        query: str,
    ):
        if query == "payment":
            return np.array(
                [1.0, 0.0]
            )

        return np.array(
            [0.0, 1.0]
        )


def test_dense_retriever_ranks_best_match_first():
    documents = {
        "payment.md": "payment document",
        "shipping.md": "shipping document",
    }

    retriever = DenseRetriever(
        documents,
        encoder=FakeEncoder(),
    )

    results = retriever.search(
        "payment",
        k=2,
    )

    assert results[0][0] == "payment.md"


def test_dense_retriever_respects_k():
    documents = {
        "payment.md": "payment document",
        "shipping.md": "shipping document",
    }

    retriever = DenseRetriever(
        documents,
        encoder=FakeEncoder(),
    )

    results = retriever.search(
        "payment",
        k=1,
    )

    assert len(results) == 1