from __future__ import annotations

import math
from collections.abc import (
    Mapping,
    Sequence,
)


ScoreMap = Mapping[str, float]

DocumentSimilarityMap = Mapping[
    str,
    Mapping[str, float],
]


def _unique_candidates(
    candidate_ids: Sequence[str],
) -> list[str]:

    return list(
        dict.fromkeys(
            candidate_ids
        )
    )


def _validate_score_maps(
    candidate_ids: Sequence[str],
    score_maps: Sequence[ScoreMap],
) -> None:

    if not score_maps:
        raise ValueError(
            "score_maps cannot be empty."
        )

    for document_id in candidate_ids:

        for index, score_map in enumerate(
            score_maps
        ):
            if document_id not in score_map:
                raise ValueError(
                    "Missing similarity score "
                    f"for {document_id!r} "
                    f"in score map {index}."
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


def normalize_score_maps(
    candidate_ids: Sequence[str],
    score_maps: Sequence[ScoreMap],
) -> list[dict[str, float]]:

    candidates = (
        _unique_candidates(
            candidate_ids
        )
    )

    _validate_score_maps(
        candidates,
        score_maps,
    )

    normalized_maps = []

    for score_map in score_maps:

        values = [
            float(
                score_map[
                    document_id
                ]
            )
            for document_id
            in candidates
        ]

        minimum = min(
            values
        )

        maximum = max(
            values
        )

        if maximum == minimum:

            normalized = {
                document_id: 0.0
                for document_id
                in candidates
            }

        else:

            scale = (
                maximum
                - minimum
            )

            normalized = {
                document_id:
                    (
                        float(
                            score_map[
                                document_id
                            ]
                        )
                        - minimum
                    )
                    / scale
                for document_id
                in candidates
            }

        normalized_maps.append(
            normalized
        )

    return normalized_maps

def query_coverage_value(
    selected_ids: Sequence[str],
    normalized_score_maps: Sequence[
        ScoreMap
    ],
) -> float:
    """Average best coverage across query formulations."""

    if not normalized_score_maps:
        raise ValueError(
            "normalized_score_maps "
            "cannot be empty."
        )

    if not selected_ids:
        return 0.0

    total = 0.0

    for score_map in (
        normalized_score_maps
    ):

        best = max(
            float(
                score_map[
                    document_id
                ]
            )
            for document_id
            in selected_ids
        )

        total += best

    return (
        total
        / len(
            normalized_score_maps
        )
    )


def greedy_query_coverage(
    candidate_ids: Sequence[str],
    score_maps: Sequence[ScoreMap],
    k: int,
) -> list[tuple[str, float]]:
    """Greedily maximize coverage across query formulations.

    Returned score is the marginal coverage gain at the
    selection step.
    """

    if k <= 0:
        raise ValueError(
            "k must be strictly positive."
        )

    candidates = (
        _unique_candidates(
            candidate_ids
        )
    )

    if not candidates:
        return []

    normalized = (
        normalize_score_maps(
            candidates,
            score_maps,
        )
    )

    relevance = {
        document_id:
            max(
                score_map[
                    document_id
                ]
                for score_map
                in normalized
            )
        for document_id
        in candidates
    }

    selected: list[str] = []
    output: list[
        tuple[str, float]
    ] = []

    remaining = set(
        candidates
    )

    current_value = 0.0

    while (
        remaining
        and len(selected) < k
    ):

        best_document = None
        best_gain = float(
            "-inf"
        )

        for document_id in sorted(
            remaining
        ):

            proposed = [
                *selected,
                document_id,
            ]

            proposed_value = (
                query_coverage_value(
                    proposed,
                    normalized,
                )
            )

            gain = (
                proposed_value
                - current_value
            )

            if (
                gain > best_gain
                or (
                    gain == best_gain
                    and (
                        best_document is None
                        or relevance[
                            document_id
                        ]
                        > relevance[
                            best_document
                        ]
                    )
                )
            ):
                best_document = (
                    document_id
                )

                best_gain = gain

        assert (
            best_document
            is not None
        )

        selected.append(
            best_document
        )

        remaining.remove(
            best_document
        )

        current_value += (
            best_gain
        )

        output.append(
            (
                best_document,
                best_gain,
            )
        )

    return output

def _normalize_document_similarity(
    similarity: float,
) -> float:

    if not math.isfinite(
        similarity
    ):
        raise ValueError(
            "Document similarity "
            "must be finite."
        )

    # Cosine similarity:
    # [-1, 1] -> [0, 1]
    return (
        similarity
        + 1.0
    ) / 2.0


def maximal_marginal_relevance(
    candidate_ids: Sequence[str],
    score_maps: Sequence[ScoreMap],
    document_similarities:
        DocumentSimilarityMap,
    k: int,
    lambda_relevance: float = 0.5,
) -> list[tuple[str, float]]:
    """Select a relevant but non-redundant evidence set."""

    if k <= 0:
        raise ValueError(
            "k must be strictly positive."
        )

    if not (
        0.0
        <= lambda_relevance
        <= 1.0
    ):
        raise ValueError(
            "lambda_relevance must "
            "be between 0 and 1."
        )

    candidates = (
        _unique_candidates(
            candidate_ids
        )
    )

    if not candidates:
        return []

    normalized_scores = (
        normalize_score_maps(
            candidates,
            score_maps,
        )
    )

    relevance = {
        document_id:
            max(
                score_map[
                    document_id
                ]
                for score_map
                in normalized_scores
            )
        for document_id
        in candidates
    }

    selected: list[str] = []

    output: list[
        tuple[str, float]
    ] = []

    remaining = set(
        candidates
    )

    while (
        remaining
        and len(selected) < k
    ):

        best_document = None
        best_score = float(
            "-inf"
        )

        for document_id in sorted(
            remaining
        ):

            if not selected:

                redundancy = 0.0

            else:

                similarities = []

                for selected_id in (
                    selected
                ):

                    try:
                        raw_similarity = (
                            document_similarities[
                                document_id
                            ][
                                selected_id
                            ]
                        )

                    except KeyError as exc:
                        raise ValueError(
                            "Missing document "
                            "similarity for "
                            f"{document_id!r} "
                            f"and "
                            f"{selected_id!r}."
                        ) from exc

                    similarities.append(
                        _normalize_document_similarity(
                            float(
                                raw_similarity
                            )
                        )
                    )

                redundancy = max(
                    similarities
                )

            mmr_score = (
                lambda_relevance
                * relevance[
                    document_id
                ]
                -
                (
                    1.0
                    - lambda_relevance
                )
                * redundancy
            )

            if (
                mmr_score
                > best_score
            ):
                best_score = (
                    mmr_score
                )

                best_document = (
                    document_id
                )

        assert (
            best_document
            is not None
        )

        selected.append(
            best_document
        )

        remaining.remove(
            best_document
        )

        output.append(
            (
                best_document,
                best_score,
            )
        )

    return output