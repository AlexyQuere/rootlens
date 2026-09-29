from rootlens.retrieval.tfidf import (
    build_vocabulary,
    cosine_similarity,
    tfidf_vector,
    tokenize,
)


class TfidfRetriever:
    """Small in-memory TF-IDF retriever.

    The corpus is indexed once during initialization.
    Queries can then reuse the precomputed document vectors.
    """

    def __init__(
        self,
        documents: dict[str, str],
    ) -> None:
        self.documents = documents

        self.document_ids = list(documents.keys())

        self.tokenized_documents = [
            tokenize(documents[document_id])
            for document_id in self.document_ids
        ]

        self.vocabulary = build_vocabulary(
            self.tokenized_documents
        )

        self.document_vectors = [
            tfidf_vector(
                tokens,
                self.tokenized_documents,
                self.vocabulary,
            )
            for tokens in self.tokenized_documents
        ]

    def search(
        self,
        query: str,
        k: int = 5,
    ) -> list[tuple[str, float]]:
        """Return the top-k documents ranked by cosine similarity."""

        query_tokens = tokenize(query)

        query_vector = tfidf_vector(
            query_tokens,
            self.tokenized_documents,
            self.vocabulary,
        )

        results: list[tuple[str, float]] = []

        for document_id, document_vector in zip(
            self.document_ids,
            self.document_vectors,
        ):
            score = cosine_similarity(
                query_vector,
                document_vector,
            )

            if score > 0.0:
                results.append(
                    (document_id, score)
                )

        results.sort(
            key=lambda item: (-item[1], item[0])
        )

        return results[:k]