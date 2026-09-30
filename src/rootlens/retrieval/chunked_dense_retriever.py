from rootlens.retrieval.chunking import (
    TextChunk,
    chunk_corpus,
)


class ChunkedDenseRetriever:
    """Dense retrieval over chunks with document-level aggregation."""

    def __init__(
        self,
        documents: dict[str, str],
        encoder,
        chunk_size_words: int,
        overlap_words: int,
    ) -> None:
        self.documents = documents
        self.encoder = encoder

        self.chunks = chunk_corpus(
            documents,
            chunk_size_words=(
                chunk_size_words
            ),
            overlap_words=overlap_words,
        )

        chunk_texts = [
            chunk.text
            for chunk in self.chunks
        ]

        self.chunk_embeddings = (
            self.encoder.encode_documents(
                chunk_texts
            )
        )

    def search_chunks(
        self,
        query: str,
        k: int = 10,
    ) -> list[tuple[TextChunk, float]]:
        if k <= 0:
            raise ValueError(
                "k must be strictly positive."
            )

        query_embedding = (
            self.encoder.encode_query(query)
        )

        scores = (
            self.chunk_embeddings
            @ query_embedding
        )

        results = [
            (
                chunk,
                float(score),
            )
            for chunk, score
            in zip(
                self.chunks,
                scores,
            )
        ]

        results.sort(
            key=lambda item: (
                -item[1],
                item[0].chunk_id,
            )
        )

        return results[:k]

    def search(
        self,
        query: str,
        k: int = 5,
    ) -> list[tuple[str, float]]:
        if k <= 0:
            raise ValueError(
                "k must be strictly positive."
            )

        query_embedding = (
            self.encoder.encode_query(query)
        )

        scores = (
            self.chunk_embeddings
            @ query_embedding
        )

        best_score_by_document: dict[
            str,
            float,
        ] = {}

        for chunk, score in zip(
            self.chunks,
            scores,
        ):
            document_id = chunk.document_id
            score = float(score)

            previous = (
                best_score_by_document.get(
                    document_id
                )
            )

            if (
                previous is None
                or score > previous
            ):
                best_score_by_document[
                    document_id
                ] = score

        results = list(
            best_score_by_document.items()
        )

        results.sort(
            key=lambda item: (
                -item[1],
                item[0],
            )
        )

        return results[:k]