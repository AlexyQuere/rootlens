from __future__ import annotations

from typing import Mapping
from typing import Protocol
from typing import Sequence


class Retriever(Protocol):

    def search(
        self,
        query: str,
        k: int,
    ) -> list[
        tuple[str, float]
    ]:
        ...


class FrozenMultiQueryRRFRetriever:
    """
    Multi-query retrieval using frozen rewrites
    and Reciprocal Rank Fusion.

    This component performs no LLM calls.

    It is intended for controlled retrieval
    experiments where query rewrites have already
    been generated and frozen.
    """

    def __init__(
        self,
        base_retriever: Retriever,
        rewrites: Mapping[
            str,
            Sequence[str],
        ],
        candidates_per_query: int = 10,
        rrf_k: int = 60,
    ) -> None:

        if candidates_per_query <= 0:
            raise ValueError(
                "candidates_per_query "
                "must be positive."
            )

        if rrf_k <= 0:
            raise ValueError(
                "rrf_k must be positive."
            )

        self.base_retriever = (
            base_retriever
        )

        self.rewrites = {
            query:
                tuple(
                    query_rewrites
                )
            for query, query_rewrites
            in rewrites.items()
        }

        self.candidates_per_query = (
            candidates_per_query
        )

        self.rrf_k = rrf_k

    @staticmethod
    def _deduplicate_queries(
        queries: Sequence[str],
    ) -> list[str]:

        result = []

        seen = set()

        for query in queries:

            normalized = (
                query.strip()
            )

            if not normalized:
                continue

            if normalized in seen:
                continue

            seen.add(
                normalized
            )

            result.append(
                normalized
            )

        return result

    def expanded_queries(
        self,
        query: str,
    ) -> list[str]:

        if query not in self.rewrites:

            raise KeyError(
                "No frozen rewrites "
                f"for query: {query}"
            )

        return (
            self._deduplicate_queries(
                [
                    query,
                    *self.rewrites[
                        query
                    ],
                ]
            )
        )

    def search(
        self,
        query: str,
        k: int,
    ) -> list[
        tuple[str, float]
    ]:

        if k <= 0:
            raise ValueError(
                "k must be positive."
            )

        queries = (
            self.expanded_queries(
                query
            )
        )

        scores: dict[
            str,
            float,
        ] = {}

        best_rank: dict[
            str,
            int,
        ] = {}

        first_seen: dict[
            str,
            int,
        ] = {}

        next_seen_index = 0

        for expanded_query in queries:

            ranking = (
                self.base_retriever.search(
                    expanded_query,
                    k=(
                        self
                        .candidates_per_query
                    ),
                )
            )

            for rank, (
                document_id,
                _,
            ) in enumerate(
                ranking,
                start=1,
            ):

                if (
                    document_id
                    not in first_seen
                ):

                    first_seen[
                        document_id
                    ] = (
                        next_seen_index
                    )

                    next_seen_index += 1

                score = (
                    1.0
                    / (
                        self.rrf_k
                        + rank
                    )
                )

                scores[
                    document_id
                ] = (
                    scores.get(
                        document_id,
                        0.0,
                    )
                    + score
                )

                best_rank[
                    document_id
                ] = min(
                    best_rank.get(
                        document_id,
                        rank,
                    ),
                    rank,
                )

        ranked = sorted(
            scores.items(),
            key=lambda item: (
                -item[1],
                best_rank[
                    item[0]
                ],
                first_seen[
                    item[0]
                ],
                item[0],
            ),
        )

        return ranked[
            :k
        ]