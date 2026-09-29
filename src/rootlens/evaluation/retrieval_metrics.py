def precision_at_k(
    retrieved: list[str],
    relevant: set[str],
    k: int,
) -> float:
    """Compute Precision@k."""

    if k <= 0:
        raise ValueError("k must be strictly positive.")

    top_k = retrieved[:k]

    relevant_retrieved = sum(
        document_id in relevant
        for document_id in top_k
    )

    return relevant_retrieved / k


def recall_at_k(
    retrieved: list[str],
    relevant: set[str],
    k: int,
) -> float:
    """Compute Recall@k."""

    if k <= 0:
        raise ValueError("k must be strictly positive.")

    if not relevant:
        return 0.0

    top_k = retrieved[:k]

    relevant_retrieved = sum(
        document_id in relevant
        for document_id in top_k
    )

    return relevant_retrieved / len(relevant)


def reciprocal_rank(
    retrieved: list[str],
    relevant: set[str],
) -> float:
    """Compute reciprocal rank for one query."""

    for rank, document_id in enumerate(
        retrieved,
        start=1,
    ):
        if document_id in relevant:
            return 1.0 / rank

    return 0.0