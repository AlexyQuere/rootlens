from __future__ import annotations

import math
from collections.abc import (
    Mapping,
    Sequence,
)


def _prepare_candidates(
    candidate_ids: Sequence[str],
    score_maps: Sequence[
        Mapping[str, float]
    ],
) -> list[str]:
    """Validate candidate scores and return unique candidates."""

    if not score_maps:
        raise ValueError(
            "score_maps cannot be empty."
        )

    candidates = list(
        dict.fromkeys(
            candidate_ids
        )
    )

    if not candidates:
        return []

    for document_id in candidates:

        for index, score_map in enumerate(
            score_maps
        ):
            if document_id not in score_map:
                raise ValueError(
                    "Missing similarity score for "
                    f"{document_id!r} in score map "
                    f"{index}."
                )

            score = float(
                score_map[
                    document_id
                ]
            )

            if not math.isfinite(
                score
            ):
                raise ValueError(
                    "Non-finite similarity score "
                    f"for {document_id!r}: "
                    f"{score}"
                )

    return candidates


def max_similarity_fusion(
    candidate_ids: Sequence[str],
    score_maps: Sequence[
        Mapping[str, float]
    ],
) -> list[tuple[str, float]]:
    """Rank candidates by their best similarity to any query.

    score(d) = max_i similarity(q_i, d)
    """

    candidates = (
        _prepare_candidates(
            candidate_ids,
            score_maps,
        )
    )

    scored = []

    for document_id in candidates:

        score = max(
            float(
                score_map[
                    document_id
                ]
            )
            for score_map
            in score_maps
        )

        scored.append(
            (
                document_id,
                score,
            )
        )

    scored.sort(
        key=lambda item: (
            -item[1],
            item[0],
        )
    )

    return scored


def mean_similarity_fusion(
    candidate_ids: Sequence[str],
    score_maps: Sequence[
        Mapping[str, float]
    ],
) -> list[tuple[str, float]]:
    """Rank candidates by mean similarity across all queries.

    score(d) = mean_i similarity(q_i, d)
    """

    candidates = (
        _prepare_candidates(
            candidate_ids,
            score_maps,
        )
    )

    scored = []

    for document_id in candidates:

        scores = [
            float(
                score_map[
                    document_id
                ]
            )
            for score_map
            in score_maps
        ]

        score = (
            sum(scores)
            / len(scores)
        )

        scored.append(
            (
                document_id,
                score,
            )
        )

    scored.sort(
        key=lambda item: (
            -item[1],
            item[0],
        )
    )

    return scored