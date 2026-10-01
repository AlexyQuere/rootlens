from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from typing import Sequence


@dataclass(frozen=True)
class QueryRAGMetrics:

    retrieval_qrel_recall: float

    citation_qrel_precision: (
        float | None
    )

    citation_qrel_recall: float

    relevant_evidence_retention: (
        float | None
    )

    source_utilization: float

    claim_count: int

    mean_sources_per_claim: float

    missing_relevant_from_retrieval: (
        tuple[str, ...]
    )

    retrieved_relevant_not_cited: (
        tuple[str, ...]
    )

    cited_qrel_irrelevant: (
        tuple[str, ...]
    )


def relevant_sources(
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


def cited_sources(
    claims: Sequence[dict],
) -> set[str]:

    result = set()

    for claim in claims:

        sources = claim.get(
            "sources",
            [],
        )

        for source in sources:

            result.add(
                source
            )

    return result


def retrieval_qrel_recall(
    retrieved: set[str],
    relevant: set[str],
) -> float:

    if not relevant:
        return 0.0

    return (
        len(
            retrieved
            & relevant
        )
        / len(relevant)
    )


def citation_qrel_precision(
    cited: set[str],
    relevant: set[str],
) -> float | None:

    if not cited:
        return None

    return (
        len(
            cited
            & relevant
        )
        / len(cited)
    )


def citation_qrel_recall(
    cited: set[str],
    relevant: set[str],
) -> float:

    if not relevant:
        return 0.0

    return (
        len(
            cited
            & relevant
        )
        / len(relevant)
    )


def relevant_evidence_retention(
    retrieved: set[str],
    cited: set[str],
    relevant: set[str],
) -> float | None:

    retrieved_relevant = (
        retrieved
        & relevant
    )

    if not retrieved_relevant:
        return None

    cited_relevant = (
        cited
        & relevant
    )

    return (
        len(cited_relevant)
        / len(retrieved_relevant)
    )


def source_utilization(
    retrieved: set[str],
    cited: set[str],
) -> float:

    if not retrieved:
        return 0.0

    return (
        len(
            cited
            & retrieved
        )
        / len(retrieved)
    )


def mean_sources_per_claim(
    claims: Sequence[dict],
) -> float:

    if not claims:
        return 0.0

    total = sum(
        len(
            set(
                claim.get(
                    "sources",
                    [],
                )
            )
        )
        for claim in claims
    )

    return (
        total
        / len(claims)
    )


def compute_query_rag_metrics(
    relevance: Mapping[
        str,
        int,
    ],
    retrieved_source_ids: Sequence[str],
    claims: Sequence[dict],
) -> QueryRAGMetrics:

    relevant = (
        relevant_sources(
            relevance
        )
    )

    retrieved = set(
        retrieved_source_ids
    )

    cited = (
        cited_sources(
            claims
        )
    )

    return QueryRAGMetrics(
        retrieval_qrel_recall=(
            retrieval_qrel_recall(
                retrieved,
                relevant,
            )
        ),

        citation_qrel_precision=(
            citation_qrel_precision(
                cited,
                relevant,
            )
        ),

        citation_qrel_recall=(
            citation_qrel_recall(
                cited,
                relevant,
            )
        ),

        relevant_evidence_retention=(
            relevant_evidence_retention(
                retrieved,
                cited,
                relevant,
            )
        ),

        source_utilization=(
            source_utilization(
                retrieved,
                cited,
            )
        ),

        claim_count=len(
            claims
        ),

        mean_sources_per_claim=(
            mean_sources_per_claim(
                claims
            )
        ),

        missing_relevant_from_retrieval=(
            tuple(
                sorted(
                    relevant
                    - retrieved
                )
            )
        ),

        retrieved_relevant_not_cited=(
            tuple(
                sorted(
                    (
                        retrieved
                        & relevant
                    )
                    - cited
                )
            )
        ),

        cited_qrel_irrelevant=(
            tuple(
                sorted(
                    cited
                    - relevant
                )
            )
        ),
    )


def validate_frozen_rag_item(
    item: dict,
) -> None:

    if not isinstance(
        item,
        dict,
    ):
        raise ValueError(
            "RAG item must be "
            "a dictionary."
        )

    evidence = item.get(
        "evidence"
    )

    answer = item.get(
        "answer"
    )

    if not isinstance(
        evidence,
        list,
    ):
        raise ValueError(
            "evidence must be a list."
        )

    if not isinstance(
        answer,
        dict,
    ):
        raise ValueError(
            "answer must be a dictionary."
        )

    retrieved = []

    for evidence_item in evidence:

        source_id = (
            evidence_item.get(
                "source_id"
            )
        )

        if (
            not isinstance(
                source_id,
                str,
            )
            or not source_id
        ):
            raise ValueError(
                "Every evidence item "
                "must have a source_id."
            )

        retrieved.append(
            source_id
        )

    if (
        len(retrieved)
        != len(set(retrieved))
    ):
        raise ValueError(
            "Frozen evidence contains "
            "duplicate source identifiers."
        )

    claims = answer.get(
        "claims"
    )

    status = answer.get(
        "status"
    )

    limitation = answer.get(
        "limitation"
    )

    if not isinstance(
        claims,
        list,
    ):
        raise ValueError(
            "answer.claims must be "
            "a list."
        )

    if status not in {
        "answered",
        "partial",
        "abstained",
    }:
        raise ValueError(
            "Invalid frozen answer "
            f"status: {status!r}"
        )

    cited = set()

    for claim in claims:

        if not isinstance(
            claim,
            dict,
        ):
            raise ValueError(
                "Every frozen claim "
                "must be an object."
            )

        text = claim.get(
            "text"
        )

        sources = claim.get(
            "sources"
        )

        if (
            not isinstance(
                text,
                str,
            )
            or not text.strip()
        ):
            raise ValueError(
                "Every frozen claim "
                "must have non-empty text."
            )

        if (
            not isinstance(
                sources,
                list,
            )
            or not sources
        ):
            raise ValueError(
                "Every frozen claim "
                "must cite at least "
                "one source."
            )

        for source in sources:

            if source not in retrieved:
                raise ValueError(
                    "Frozen claim cites "
                    "a source that was "
                    "not retrieved: "
                    f"{source}"
                )

            cited.add(
                source
            )

    if status == "answered":

        if not claims:
            raise ValueError(
                "answered output must "
                "contain claims."
            )

        if limitation is not None:
            raise ValueError(
                "answered output must "
                "not have a limitation."
            )

    elif status == "partial":

        if not claims:
            raise ValueError(
                "partial output must "
                "contain claims."
            )

        if (
            not isinstance(
                limitation,
                str,
            )
            or not limitation.strip()
        ):
            raise ValueError(
                "partial output must "
                "contain a limitation."
            )

    else:

        if claims:
            raise ValueError(
                "abstained output must "
                "not contain claims."
            )

        if (
            not isinstance(
                limitation,
                str,
            )
            or not limitation.strip()
        ):
            raise ValueError(
                "abstained output must "
                "contain a limitation."
            )