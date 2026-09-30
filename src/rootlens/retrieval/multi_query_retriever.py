from __future__ import annotations

from dataclasses import dataclass

from rootlens.retrieval.query_rewriter import (
    QueryRewriter,
)


@dataclass(frozen=True)
class QueryRanking:
    query: str
    results: list[tuple[str, float]]


@dataclass(frozen=True)
class MultiQuerySearchResult:
    expanded_queries: list[str]
    rankings: list[QueryRanking]
    union_document_ids: list[str]
    fused_results: list[tuple[str, float]]


def reciprocal_rank_fusion(
    rankings: list[
        list[tuple[str, float]]
    ],
    rrf_k: int = 60,
) -> list[tuple[str, float]]:
    """Fuse rankings using Reciprocal Rank Fusion.

    Original retrieval scores are deliberately ignored.

    Each document receives:

        sum 1 / (rrf_k + rank)

    across every ranking in which it appears.
    """

    if rrf_k <= 0:
        raise ValueError(
            "rrf_k must be strictly positive."
        )

    scores: dict[str, float] = {}

    for ranking in rankings:

        for rank, (
            document_id,
            _,
        ) in enumerate(
            ranking,
            start=1,
        ):
            scores[
                document_id
            ] = (
                scores.get(
                    document_id,
                    0.0,
                )
                + 1.0
                / (
                    rrf_k
                    + rank
                )
            )

    fused = list(
        scores.items()
    )

    fused.sort(
        key=lambda item: (
            -item[1],
            item[0],
        )
    )

    return fused


class MultiQueryRetriever:
    """Retrieve with the original query and semantic rewrites."""

    def __init__(
        self,
        retriever,
        query_rewriter: QueryRewriter,
        num_rewrites: int = 3,
        candidates_per_query: int = 10,
        rrf_k: int = 60,
    ) -> None:

        if num_rewrites <= 0:
            raise ValueError(
                "num_rewrites must be "
                "strictly positive."
            )

        if candidates_per_query <= 0:
            raise ValueError(
                "candidates_per_query must "
                "be strictly positive."
            )

        if rrf_k <= 0:
            raise ValueError(
                "rrf_k must be "
                "strictly positive."
            )

        self.retriever = retriever
        self.query_rewriter = (
            query_rewriter
        )

        self.num_rewrites = (
            num_rewrites
        )

        self.candidates_per_query = (
            candidates_per_query
        )

        self.rrf_k = rrf_k

    def expand_queries(
        self,
        query: str,
    ) -> list[str]:

        rewrites = (
            self.query_rewriter.rewrite(
                query,
                n=self.num_rewrites,
            )
        )

        expanded = [
            query,
            *rewrites,
        ]

        # Defensive de-duplication.
        result = []
        seen = set()

        for expanded_query in expanded:

            normalized = " ".join(
                expanded_query
                .lower()
                .split()
            )

            if normalized in seen:
                continue

            seen.add(
                normalized
            )

            result.append(
                expanded_query
            )

        return result

    def search_with_details(
        self,
        query: str,
        k: int = 5,
    ) -> MultiQuerySearchResult:

        if k <= 0:
            raise ValueError(
                "k must be strictly positive."
            )

        expanded_queries = (
            self.expand_queries(
                query
            )
        )

        rankings: list[
            QueryRanking
        ] = []

        ranking_lists = []

        union_document_ids = []
        seen_documents = set()

        for expanded_query in (
            expanded_queries
        ):

            results = (
                self.retriever.search(
                    expanded_query,
                    k=(
                        self
                        .candidates_per_query
                    ),
                )
            )

            rankings.append(
                QueryRanking(
                    query=(
                        expanded_query
                    ),
                    results=results,
                )
            )

            ranking_lists.append(
                results
            )

            for (
                document_id,
                _,
            ) in results:

                if (
                    document_id
                    in seen_documents
                ):
                    continue

                seen_documents.add(
                    document_id
                )

                union_document_ids.append(
                    document_id
                )

        fused = (
            reciprocal_rank_fusion(
                ranking_lists,
                rrf_k=self.rrf_k,
            )
        )

        return (
            MultiQuerySearchResult(
                expanded_queries=(
                    expanded_queries
                ),
                rankings=rankings,
                union_document_ids=(
                    union_document_ids
                ),
                fused_results=(
                    fused[:k]
                ),
            )
        )

    def search(
        self,
        query: str,
        k: int = 5,
    ) -> list[tuple[str, float]]:

        return (
            self.search_with_details(
                query,
                k=k,
            )
            .fused_results
        )