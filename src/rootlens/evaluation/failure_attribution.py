from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from typing import Sequence


@dataclass(frozen=True)
class EvidenceIntervention:

    baseline_ids: tuple[
        str,
        ...
    ]

    enriched_ids: tuple[
        str,
        ...
    ]

    positive_qrel_ids: tuple[
        str,
        ...
    ]

    recovered_qrel_ids: tuple[
        str,
        ...
    ]

    dropped_baseline_ids: tuple[
        str,
        ...
    ]

    omitted_positive_qrel_ids: tuple[
        str,
        ...
    ]


def positive_qrel_sources(
    relevance: Mapping[
        str,
        int,
    ],
) -> set[str]:

    return {
        source_id
        for source_id, grade
        in relevance.items()
        if grade > 0
    }


def build_qrel_enriched_context(
    baseline_ids: Sequence[str],
    relevance: Mapping[
        str,
        int,
    ],
    k: int,
) -> EvidenceIntervention:

    if k <= 0:
        raise ValueError(
            "k must be positive."
        )

    baseline = list(
        baseline_ids
    )

    if not baseline:
        raise ValueError(
            "baseline_ids cannot "
            "be empty."
        )

    if (
        len(baseline)
        != len(set(baseline))
    ):
        raise ValueError(
            "baseline_ids contain "
            "duplicates."
        )

    baseline_position = {
        source_id:
            index
        for index, source_id
        in enumerate(
            baseline
        )
    }

    positive = [
        source_id
        for source_id, grade
        in relevance.items()
        if grade > 0
    ]

    if not positive:
        raise ValueError(
            "No positive qrel "
            "documents found."
        )

    #
    # Primary evidence first
    # (grade 2 before grade 1).
    #
    # When grades are equal,
    # preserve Dense ordering when
    # the document was already
    # retrieved.
    #
    positive.sort(
        key=lambda source_id: (
            -relevance[
                source_id
            ],
            baseline_position.get(
                source_id,
                10**9,
            ),
            source_id,
        )
    )

    enriched = []

    #
    # First allocate the matched
    # context budget to qrel-positive
    # evidence.
    #
    for source_id in positive:

        if len(enriched) >= k:
            break

        enriched.append(
            source_id
        )

    #
    # Fill unused slots using the
    # original Dense ranking.
    #
    for source_id in baseline:

        if len(enriched) >= k:
            break

        if source_id in enriched:
            continue

        enriched.append(
            source_id
        )

    baseline_set = set(
        baseline
    )

    enriched_set = set(
        enriched
    )

    positive_set = set(
        positive
    )

    recovered = (
        enriched_set
        & positive_set
        - baseline_set
    )

    dropped = (
        baseline_set
        - enriched_set
    )

    omitted_positive = (
        positive_set
        - enriched_set
    )

    return EvidenceIntervention(
        baseline_ids=tuple(
            baseline
        ),

        enriched_ids=tuple(
            enriched
        ),

        positive_qrel_ids=tuple(
            positive
        ),

        recovered_qrel_ids=tuple(
            sorted(
                recovered
            )
        ),

        dropped_baseline_ids=tuple(
            source_id
            for source_id
            in baseline
            if source_id in dropped
        ),

        omitted_positive_qrel_ids=tuple(
            sorted(
                omitted_positive
            )
        ),
    )


def citation_qrel_recall(
    cited_sources: set[str],
    relevance: Mapping[
        str,
        int,
    ],
) -> float:

    relevant = (
        positive_qrel_sources(
            relevance
        )
    )

    if not relevant:
        return 0.0

    return (
        len(
            cited_sources
            & relevant
        )
        / len(relevant)
    )


def recovered_evidence_uptake(
    cited_sources: set[str],
    intervention: EvidenceIntervention,
) -> float | None:

    recovered = set(
        intervention
        .recovered_qrel_ids
    )

    if not recovered:
        return None

    return (
        len(
            cited_sources
            & recovered
        )
        / len(recovered)
    )