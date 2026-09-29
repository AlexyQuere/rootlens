class HybridRetriever:
    """Combine lexical and dense rankings using Reciprocal Rank Fusion."""

    def __init__(
        self,
        lexical_retriever,
        dense_retriever,
        rrf_k: int = 60,
    ) -> None:
        if rrf_k <= 0:
            raise ValueError(
                "rrf_k must be strictly positive."
            )

        self.lexical_retriever = lexical_retriever
        self.dense_retriever = dense_retriever
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        k: int = 5,
        candidate_k: int = 20,
    ) -> list[tuple[str, float]]:
        """Return documents ranked using Reciprocal Rank Fusion."""

        if k <= 0:
            raise ValueError(
                "k must be strictly positive."
            )

        if candidate_k <= 0:
            raise ValueError(
                "candidate_k must be strictly positive."
            )

        lexical_results = (
            self.lexical_retriever.search(
                query,
                k=candidate_k,
            )
        )

        dense_results = (
            self.dense_retriever.search(
                query,
                k=candidate_k,
            )
        )

        rrf_scores: dict[str, float] = {}

        for rank, (
            document_id,
            _,
        ) in enumerate(
            lexical_results,
            start=1,
        ):
            rrf_scores[document_id] = (
                rrf_scores.get(
                    document_id,
                    0.0,
                )
                + 1.0
                / (
                    self.rrf_k
                    + rank
                )
            )

        for rank, (
            document_id,
            _,
        ) in enumerate(
            dense_results,
            start=1,
        ):
            rrf_scores[document_id] = (
                rrf_scores.get(
                    document_id,
                    0.0,
                )
                + 1.0
                / (
                    self.rrf_k
                    + rank
                )
            )

        ranked_results = sorted(
            rrf_scores.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        )

        return ranked_results[:k]