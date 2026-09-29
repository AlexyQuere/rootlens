import math

from rootlens.retrieval.tfidf import (
    term_frequency,
    tokenize,
)


class BM25Retriever:
    """Small in-memory BM25 retriever."""

    def __init__(
        self,
        documents: dict[str, str],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be strictly positive.")

        if not 0.0 <= b <= 1.0:
            raise ValueError("b must be between 0 and 1.")

        self.documents = documents
        self.document_ids = list(documents.keys())

        self.k1 = k1
        self.b = b

        self.tokenized_documents = [
            tokenize(documents[document_id])
            for document_id in self.document_ids
        ]

        self.document_lengths = [
            len(tokens)
            for tokens in self.tokenized_documents
        ]

        if self.document_lengths:
            self.average_document_length = (
                sum(self.document_lengths)
                / len(self.document_lengths)
            )
        else:
            self.average_document_length = 0.0

        self.term_frequencies = [
            term_frequency(tokens)
            for tokens in self.tokenized_documents
        ]

        self.document_frequencies = (
            self._build_document_frequencies()
        )

    def _build_document_frequencies(
        self,
    ) -> dict[str, int]:
        """Compute document frequency for every term."""

        frequencies: dict[str, int] = {}

        for document in self.tokenized_documents:
            for term in set(document):
                frequencies[term] = (
                    frequencies.get(term, 0) + 1
                )

        return frequencies

    def _idf(self, term: str) -> float:
        """Compute BM25 IDF for one term."""

        number_of_documents = len(
            self.tokenized_documents
        )

        document_frequency = (
            self.document_frequencies.get(term, 0)
        )

        if (
            number_of_documents == 0
            or document_frequency == 0
        ):
            return 0.0

        return math.log(
            1
            + (
                number_of_documents
                - document_frequency
                + 0.5
            )
            / (
                document_frequency
                + 0.5
            )
        )

    def _score_document(
        self,
        query_tokens: list[str],
        document_index: int,
    ) -> float:
        """Compute BM25 score for one document."""

        if self.average_document_length == 0.0:
            return 0.0

        frequencies = self.term_frequencies[
            document_index
        ]

        document_length = self.document_lengths[
            document_index
        ]

        score = 0.0

        # Sorted for deterministic accumulation.
        for term in sorted(set(query_tokens)):
            tf = frequencies.get(term, 0)

            if tf == 0:
                continue

            idf = self._idf(term)

            length_normalization = (
                1
                - self.b
                + self.b
                * document_length
                / self.average_document_length
            )

            numerator = tf * (self.k1 + 1)

            denominator = (
                tf
                + self.k1
                * length_normalization
            )

            score += (
                idf
                * numerator
                / denominator
            )

        return score

    def search(
        self,
        query: str,
        k: int = 5,
    ) -> list[tuple[str, float]]:
        """Return the top-k documents ranked with BM25."""

        if k <= 0:
            raise ValueError("k must be strictly positive.")

        query_tokens = tokenize(query)

        results: list[tuple[str, float]] = []

        for document_index, document_id in enumerate(
            self.document_ids
        ):
            score = self._score_document(
                query_tokens,
                document_index,
            )

            if score > 0.0:
                results.append(
                    (document_id, score)
                )

        results.sort(
            key=lambda item: (-item[1], item[0])
        )

        return results[:k]